# frozen_string_literal: true

require_relative "plan"
require_relative "model_state"
require_relative "recovery"
require_relative "plan_checkpoint"

module TuSketchupAgent
  module PlanExecutor
    extend self

    def execute(plan, router: TuSketchupAgent::Router, base_request_id: nil, **options)
      resume = options.key?(:resume) ? !!options[:resume] : false
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
      current_state = ModelState.state(model)
      checkpoint = PlanCheckpoint.get(plan_id)
      start_index = 0

      if resume
        unless checkpoint
          return {
            ok: false,
            error: { code: "PLAN_CHECKPOINT_NOT_FOUND", message: "Không tìm thấy checkpoint cho plan_id" },
            plan_id: plan_id,
            recovery: {
              contract_version: Recovery::CONTRACT_VERSION,
              action: "START_PLAN_FROM_BEGINNING",
              retry_safe: false,
              mutation_committed: nil,
              retry_after: "new_execution"
            }
          }
        end

        unless PlanCheckpoint.compatible?(checkpoint, current_state)
          return {
            ok: false,
            error: { code: "PLAN_CHECKPOINT_STALE", message: "Checkpoint không còn khớp model session/revision hiện tại" },
            plan_id: plan_id,
            checkpoint: checkpoint,
            model_state: current_state,
            recovery: {
              contract_version: Recovery::CONTRACT_VERSION,
              action: "REFRESH_MODEL_STATE_AND_REPLAN",
              retry_safe: false,
              mutation_committed: nil,
              retry_after: "refresh_model_state"
            }
          }
        end

        completed_ids = Array(checkpoint[:completed_step_ids]).map(&:to_s)
        start_index = normalized[:steps].index { |step| !completed_ids.include?(step[:step_id].to_s) } || normalized[:steps].length
      end

      request_prefix = base_request_id.to_s.strip
      request_prefix = "plan_#{plan_id}" if request_prefix.empty?

      started_at = Process.clock_gettime(Process::CLOCK_MONOTONIC)
      step_results = []
      state_before = current_state
      normalized[:steps].each_with_index do |step, index|
        next if index < start_index

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

        after_step_state = ModelState.state(model)
        step_result = {
          step_index: index,
          step_id: step[:step_id],
          command: step[:command],
          request_id: step_request_id,
          ok: response[:ok] == true,
          response: response,
          model_revision_before: current_state[:revision],
          model_revision_after: after_step_state[:revision]
        }
        step_results << step_result

        unless response[:ok] == true
          PlanCheckpoint.save(
            plan_id,
            after_step_state,
            step_results.select { |item| item[:ok] },
            status: "failed",
            failed_step_index: index
          )
          return {
            ok: false,
            error: { code: "PLAN_STEP_FAILED", message: "Plan dừng tại step #{index + 1}: #{step[:step_id]}" },
            plan_id: plan_id,
            contract_version: Plan::CONTRACT_VERSION,
            status: "failed",
            failed_step_index: index,
            failed_step_id: step[:step_id],
            resumed: resume,
            resumed_from_step_index: start_index,
            steps: step_results,
            checkpoint: PlanCheckpoint.get(plan_id),
            model_state: after_step_state,
            duration_ms: elapsed_ms(started_at),
            recovery: {
              contract_version: Recovery::CONTRACT_VERSION,
              action: "INSPECT_FAILED_STEP_AND_REPLAN_OR_RESUME",
              retry_safe: false,
              mutation_committed: response[:mutation_committed],
              retry_after: "inspect_checkpoint"
            }
          }
        end

        PlanCheckpoint.save(
          plan_id,
          after_step_state,
          step_results.select { |item| item[:ok] },
          status: "running"
        )
      end

      state_after = ModelState.state(model)
      checkpoint_after = PlanCheckpoint.save(
        plan_id,
        state_after,
        step_results.select { |item| item[:ok] },
        status: "completed"
      )
      {
        ok: true,
        plan_id: plan_id,
        contract_version: Plan::CONTRACT_VERSION,
        status: "completed",
        resumed: resume,
        resumed_from_step_index: start_index,
        step_count: normalized[:steps].length,
        steps: step_results,
        checkpoint: checkpoint_after || PlanCheckpoint.get(plan_id),
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
