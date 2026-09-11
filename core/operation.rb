# frozen_string_literal: true

module TuSketchupAgent
  module Operation
    extend self

    @model_revision = 0

    def model_revision
      @model_revision ||= 0
    end

    def bump_model_revision
      @model_revision = (@model_revision || 0) + 1
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

      started = false
      model.start_operation(op_name, true, false, trans)
      started = true
      result = yield
      started = false
      model.commit_operation
      result
    rescue StandardError
      model.abort_operation if started
      raise
    end
  end

  # Module-level delegates for backward compatibility
  def self.model_revision
    Operation.model_revision
  end

  def self.bump_model_revision
    Operation.bump_model_revision
  end

  def self.with_operation(model_or_name, name_or_transparent = nil, transparent = false, &block)
    Operation.with_operation(model_or_name, name_or_transparent, transparent, &block)
  end
end
