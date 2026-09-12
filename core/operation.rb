# frozen_string_literal: true

require_relative "model_state"

module TuSketchupAgent
  module Operation
    extend self

    def model_revision(model = nil)
      TuSketchupAgent::ModelState.revision(model)
    end

    # Revision changes requested from inside a transaction are deferred until
    # commit. This keeps the model revision aligned with the actual committed
    # SketchUp transaction and prevents aborted operations from advancing it.
    def bump_model_revision(model = nil)
      model ||= Sketchup.active_model
      raise "No active model" unless model

      if @operation_context && @operation_context[:model].equal?(model)
        @operation_context[:revision_requested] = true
        @operation_context[:revision_request_count] += 1
        @operation_context[:revision]
      else
        TuSketchupAgent::ModelState.bump_revision(model)
      end
    end

    # Stable transaction metadata exposed to the Router/MCP response contract.
    # Keep this derived from the operation context so callers do not need to
    # infer revision changes from the top-level model_revision field.
    def transaction_metadata(transaction = nil)
      tx = transaction || last_transaction
      return tx unless tx.is_a?(Hash)

      before = tx[:revision_before]
      after = tx[:revision_after]
      delta = if !before.nil? && !after.nil?
        after.to_i - before.to_i
      end

      {
        status: tx[:status],
        operation: tx[:operation],
        revision_requested: tx[:revision_requested] == true,
        revision_request_count: tx[:revision_request_count].to_i,
        revision_bumped: tx[:revision_bumped] == true,
        revision_before: before,
        revision_after: after,
        revision_delta: delta
      }
    end

    def last_transaction
      @last_transaction || {
        status: "not_started",
        operation: nil,
        revision_requested: false,
        revision_request_count: 0,
        revision_bumped: false,
        revision_before: nil,
        revision_after: nil
      }
    end

    def with_operation(model_or_name, name_or_transparent = nil, transparent = false)
      if model_or_name.is_a?(Sketchup::Model)
        model = model_or_name
        op_name = name_or_transparent || "Operation"
        trans = transparent
      else
        model = Sketchup.active_model
        op_name = model_or_name || "Operation"
        trans = name_or_transparent || false
      end
      raise "No active model" unless model

      TuSketchupAgent::ModelState.ensure_model!(model)
      revision_before = TuSketchupAgent::ModelState.revision(model)

      previous_context = @operation_context
      @operation_context = {
        model: model,
        revision_requested: false,
        revision_request_count: 0,
        revision: revision_before,
        revision_before: revision_before
      }

      started = false
      @last_transaction = {
        status: "started",
        operation: op_name,
        revision_requested: false,
        revision_request_count: 0,
        revision_bumped: false,
        revision_before: revision_before,
        revision_after: revision_before
      }

      model.start_operation(op_name, true, false, trans)
      started = true
      result = yield

      # Only commit first. A successful commit is the point at which the
      # deferred revision becomes visible to the model-state contract.
      model.commit_operation
      started = false

      context = @operation_context
      if context[:revision_requested]
        context[:revision] = TuSketchupAgent::ModelState.bump_revision(model)
      end

      revision_after = context[:revision]
      @last_transaction = {
        status: "committed",
        operation: op_name,
        revision_requested: context[:revision_requested],
        revision_request_count: context[:revision_request_count],
        revision_bumped: context[:revision_requested],
        revision_before: context[:revision_before],
        revision_after: revision_after
      }
      result
    rescue StandardError
      model.abort_operation if started
      context = @operation_context
      revision_after = TuSketchupAgent::ModelState.revision(model)
      @last_transaction = {
        status: "aborted",
        operation: op_name,
        revision_requested: context ? context[:revision_requested] : false,
        revision_request_count: context ? context[:revision_request_count] : 0,
        revision_bumped: false,
        revision_before: context ? context[:revision_before] : revision_after,
        revision_after: revision_after
      }
      raise
    ensure
      @operation_context = previous_context
    end
  end

  # Module-level delegates for backward compatibility
  def self.model_revision(model = nil)
    Operation.model_revision(model)
  end

  def self.bump_model_revision(model = nil)
    Operation.bump_model_revision(model)
  end

  def self.transaction_metadata(transaction = nil)
    Operation.transaction_metadata(transaction)
  end

  def self.last_transaction
    Operation.last_transaction
  end

  def self.with_operation(model_or_name, name_or_transparent = nil, transparent = false, &block)
    Operation.with_operation(model_or_name, name_or_transparent, transparent, &block)
  end
end
