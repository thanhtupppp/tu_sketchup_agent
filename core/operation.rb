# frozen_string_literal: true

module TuSketchupAgent
  module Operation
    extend self

    def model_revision(model = nil)
      ModelState.revision(model)
    end

    def bump_model_revision(model = nil)
      ModelState.bump_revision(model)
    end

    def last_transaction
      @last_transaction || {
        status: "not_started",
        operation: nil
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

      ModelState.ensure_model!(model)

      started = false
      @last_transaction = {
        status: "started",
        operation: op_name
      }

      model.start_operation(op_name, true, false, trans)
      started = true
      result = yield
      started = false
      model.commit_operation
      @last_transaction = {
        status: "committed",
        operation: op_name
      }
      result
    rescue StandardError
      model.abort_operation if started
      @last_transaction = {
        status: "aborted",
        operation: op_name
      }
      raise
    end
  end

  # Module-level delegates for backward compatibility
  def self.model_revision(model = nil)
    Operation.model_revision(model)
  end

  def self.bump_model_revision(model = nil)
    Operation.bump_model_revision(model)
  end

  def self.last_transaction
    Operation.last_transaction
  end

  def self.with_operation(model_or_name, name_or_transparent = nil, transparent = false, &block)
    Operation.with_operation(model_or_name, name_or_transparent, transparent, &block)
  end
end
