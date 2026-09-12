# frozen_string_literal: true

module TuSketchupAgent
  module Plan
    extend self

    CONTRACT_VERSION = 1
    MAX_STEPS = 32
    PLAN_REQUIRED_KEYS = %w[plan_id steps].freeze

    def validate(plan, router_commands: [])
      errors = []
      warnings = []

      unless plan.is_a?(Hash)
        return invalid("Plan phải là Hash/object")
      end

      missing = PLAN_REQUIRED_KEYS.reject { |key| plan.key?(key) || plan.key?(key.to_sym) }
      missing.each { |key| errors << "Thiếu trường bắt buộc: #{key}" }

      plan_id = value(plan, "plan_id")
      errors << "plan_id không được rỗng" if plan_id.to_s.strip.empty?

      steps = value(plan, "steps")
      unless steps.is_a?(Array)
        errors << "steps phải là Array"
        return result(false, plan_id, 0, errors, warnings)
      end

      if steps.empty?
        errors << "Plan phải có ít nhất 1 step"
      elsif steps.length > MAX_STEPS
        errors << "Plan vượt quá #{MAX_STEPS} steps"
      end

      commands = Array(router_commands).map(&:to_s)
      steps.each_with_index do |step, index|
        prefix = "steps[#{index}]"
        unless step.is_a?(Hash)
          errors << "#{prefix} phải là Object/Hash"
          next
        end

        step_id = value(step, "step_id")
        command = value(step, "command").to_s
        arguments = value(step, "arguments")

        errors << "#{prefix}.step_id không được rỗng" if step_id.to_s.strip.empty?
        errors << "#{prefix}.command không được rỗng" if command.strip.empty?
        if !commands.empty? && !command.empty? && !commands.include?(command)
          errors << "#{prefix}.command không được đăng ký: #{command}"
        end
        unless arguments.nil? || arguments.is_a?(Hash)
          errors << "#{prefix}.arguments phải là Object/Hash"
        end

        if value(step, "expected_model_revision").nil? && value(step, "expected_model_session_id").nil?
          warnings << "#{prefix} chưa pin expected_model_revision/session; executor nên lấy model state trước khi chạy step"
        end
      end

      result(errors.empty?, plan_id, steps.length, errors, warnings)
    end

    def normalize(plan)
      {
        plan_id: value(plan, "plan_id").to_s,
        steps: Array(value(plan, "steps")).map.with_index do |step, index|
          step = {} unless step.is_a?(Hash)
          {
            step_id: (value(step, "step_id") || "step_#{index + 1}").to_s,
            command: value(step, "command").to_s,
            arguments: value(step, "arguments").is_a?(Hash) ? value(step, "arguments") : {}
          }
        end,
        contract_version: CONTRACT_VERSION
      }
    end

    private

    def value(hash, key)
      hash[key] || hash[key.to_sym]
    end

    def result(valid, plan_id, step_count, errors, warnings)
      {
        valid: valid,
        contract_version: CONTRACT_VERSION,
        plan_id: plan_id.to_s,
        step_count: step_count,
        max_steps: MAX_STEPS,
        errors: errors,
        warnings: warnings
      }
    end

    def invalid(message)
      result(false, nil, 0, [message], [])
    end
  end
end
