# frozen_string_literal: true

require_relative "plan"
require_relative "model_state"
require_relative "recovery"

module TuSketchupAgent
  module PlanExecutor
    extend self

    def execute(plan, router: TuSketchupAgent::Router, base_request_id: nil)
      validation = Plan.validate(plan, router_commands: router.registered_commands)
      unless validation[:valid]
        return {
          ok: false,
          error: { code: "PLAN_INVALID", message: "Plan không hợp lệ" },
          plan_validation: validation,
          recovery: Recovery.policy_for("PLAN_INVALID").merge(contract_version: Recovery::CONTRACT_VERSION)
        }
      end

      normalized = Plan.normalize(plan)
      model = Sketchup.active_model
      unless model
        return {
          ok: false,
          error: { code: "NO_ACTIVE_MODEL", message: "Không có model nào đang mở" },
          recovery: Recovery.policy_for("NO_ACTIVE_MODEL").merge(contract_version: Recovery::CONTRACT_VERSION)
        }
      end

      plan_id = normalized[:plan_id]
      request_prefix = base_request_id.to_s.strip
      request_prefix = "plan_#{plan_id}" if request_prefix.empty?

      started_at = Process.clock_gettime(Process::CLOCK_MONOTONIC)
      step_results = []
      state_before = ModelState.state(model)

      normalized[:steps].each_with_index do |step, index|
        current_state = ModelState.state(model)
        args = deep_dup(step[:arguments])
        args = {} unless args.is_a?(Hash)
        args["expected_model_revision"] = current_state[:revision]
        args["expected_model_session_id"] = current_state[:model_session_id]

        step_request_id = "#{request_prefix}:#{index + 1}:#{step[:step_id]}"
        response = router.dispatch(
          {
            "token" => TuSketchupAgent::TOKEN,
            "command" => step[:command],
            "request_id" => step_request_id,
            "arguments" => args
          }
        )

        step_results << {
          step_index: index,
          step_id: step[:step_id],
          command: step[:command],
          request_id: step_request_id,
          ok: response[:ok] == true,
          response: response,
          model_revision_before: current_state[:revision],
          model_revision_after: ModelState.state(model)[:revision]
        }

        unless response[:ok] == true
          return {
            ok: false,
            error: { code: "PLAN_STEP_FAILED", message: "Plan dừng tại step #{index + 1}: #{step[:step_id]}" },
            plan_id: plan_id,
            contract_version: Plan::CONTRACT_VERSION,
            status: "failed",
            failed_step_index: index,
            failed_step_id: step[:step_id],
            completed_steps: step_results.take(index),
            steps: step_results,
            model_state: ModelState.state(model),
            duration_ms: elapsed_ms(started_at),
            recovery: {
              contract_version: Recovery::CONTRACT_VERSION,
              action: "INSPECT_FAILED_STEP_AND_REPLAN",
              retry_safe: false,
              mutation_committed: response[:mutation_committed],
              retry_after: "inspect_failed_step"
            }
          }
        end
      end

      state_after = ModelState.state(model)
      {
        ok: true,
        plan_id: plan_id,
        contract_version: Plan::CONTRACT_VERSION,
        status: "completed",
        step_count: step_results.length,
        steps: step_results,
        model_state_before: state_before,
        model_state_after: state_after,
        duration_ms: elapsed_ms(started_at)
      }
    end

    private

    def elapsed_ms(started_at)
      ((Process.clock_gettime(Process::CLOCK_MONOTONIC) - started_at) * 1000).round(2)
    end

    def deep_dup(value)
      Marshal.load(Marshal.dump(value))
    rescue StandardError
      value
    end
  end
end
