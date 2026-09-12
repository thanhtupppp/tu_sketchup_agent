# frozen_string_literal: true

module TuSketchupAgent
  module PlanCheckpoint
    extend self

    CACHE_LIMIT = 64
    @entries = {}
    @order = []

    def save(plan_id, model_state, completed_steps, status: "running", failed_step_index: nil, outputs: {})
      key = plan_id.to_s
      return nil if key.empty?

      entry = {
        plan_id: key,
        contract_version: 2,
        model_session_id: model_state[:model_session_id],
        model_revision: model_state[:revision],
        completed_step_ids: Array(completed_steps).map { |step| step[:step_id].to_s },
        completed_count: Array(completed_steps).length,
        outputs: deep_dup(outputs || {}),
        status: status.to_s,
        failed_step_index: failed_step_index,
        updated_at_unix: Time.now.to_f
      }
      @entries[key] = entry
      touch(key)
      trim!
      deep_dup(entry)
    end

    def get(plan_id)
      entry = @entries[plan_id.to_s]
      entry && deep_dup(entry)
    end

    def clear(plan_id)
      key = plan_id.to_s
      @entries.delete(key)
      @order.delete(key)
      nil
    end

    def compatible?(checkpoint, model_state)
      return false unless checkpoint.is_a?(Hash)
      checkpoint[:model_session_id].to_s == model_state[:model_session_id].to_s &&
        checkpoint[:model_revision].to_i == model_state[:revision].to_i
    end

    private

    def deep_dup(value)
      Marshal.load(Marshal.dump(value))
    rescue StandardError
      value
    end

    def touch(key)
      @order.delete(key)
      @order << key
    end

    def trim!
      while @order.length > CACHE_LIMIT
        oldest = @order.shift
        @entries.delete(oldest)
      end
    end
  end
end
