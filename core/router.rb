# frozen_string_literal: true

require_relative "model_state"
require_relative "verification"

module TuSketchupAgent
  module Router
    extend self

    @handlers = {}

    def register(command, &block)
      @handlers[command.to_s] = block
    end

    def handler_for(command)
      @handlers[command.to_s]
    end

    def registered_commands
      @handlers.keys
    end

    def clear_handlers!
      @handlers.clear
    end

    def dispatch(payload)
      request_id = payload["request_id"].to_s
      command = payload["command"].to_s
      started_at = Process.clock_gettime(Process::CLOCK_MONOTONIC)

      unless Auth.verify_token(payload["token"])
        return Response.error(request_id, command, "UNAUTHORIZED", "Invalid token")
      end

      args = payload["arguments"]
      args = {} unless args.is_a?(Hash)

      # Optional optimistic-concurrency guard. Clients can pin a command to
      # both the current model session and revision to avoid acting on stale state.
      expected_revision = args["expected_model_revision"]
      expected_session_id = args["expected_model_session_id"]
      guarded = !expected_revision.nil? || !expected_session_id.nil?
      before_state = nil

      if guarded
        model = Sketchup.active_model
        return Response.error(request_id, command, "NO_ACTIVE_MODEL", "Không có model nào đang mở") unless model

        before_state = TuSketchupAgent::ModelState.state(model)
        revision_matches = expected_revision.nil? || TuSketchupAgent::ModelState.matches_revision?(expected_revision, model)
        session_matches = expected_session_id.nil? || expected_session_id.to_s == before_state[:model_session_id].to_s

        unless revision_matches && session_matches
          return Response.error(
            request_id,
            command,
            "STALE_MODEL_STATE",
            "Model state đã thay đổi; hãy đọc lại get_model_state trước khi thực hiện lệnh",
            "TuSketchupAgent::StaleModelStateError"
          ).merge(
            expected_model_revision: expected_revision,
            actual_model_revision: before_state[:revision],
            expected_model_session_id: expected_session_id,
            actual_model_session_id: before_state[:model_session_id]
          )
        end
      end

      handler = @handlers[command]
      result = if handler
        handler.call(args)
      else
        case command
        when "toggle_dev_mode"
          Response.error(request_id, command, "FORBIDDEN", "Dev mode chỉ được bật/tắt trực tiếp từ menu SketchUp hoặc biến môi trường")
        when "reload_extension"
          Response.error(request_id, command, "FORBIDDEN", "Reload extension chỉ được thực hiện trực tiếp từ menu SketchUp")
        else
          Response.error(request_id, command, "UNKNOWN_COMMAND", "Unknown command: #{command}")
        end
      end

      result = {
        ok: false,
        error: {
          code: "INVALID_HANDLER_RESPONSE",
          message: "Command handler không trả về Hash"
        }
      } unless result.is_a?(Hash)

      if result[:ok] == false && result[:error].is_a?(String)
        result[:error] = {
          code: "HANDLER_ERROR",
          message: result[:error],
          class: result[:error_class]
        }
        result.delete(:error_class)
      end

      if guarded && before_state
        model = Sketchup.active_model
        after_state = TuSketchupAgent::ModelState.state(model)
        verification = TuSketchupAgent::Verification.contract(
          command: command,
          before_state: before_state,
          after_state: after_state,
          transaction: Operation.last_transaction,
          handler_ok: result[:ok] == true,
          result: result,
          model: model,
          args: args
        )
        result[:verification] = verification

        if result[:ok] == true && !verification[:verified]
          # Verification runs after the handler's transaction has returned.
          # At this point SketchUp may already have committed the mutation, so
          # never imply that TRANSACTION_VERIFICATION_FAILED means rollback.
          # The caller must inspect the returned model state before retrying.
          return Response.error(
            request_id,
            command,
            "TRANSACTION_VERIFICATION_FAILED",
            "Lệnh báo thành công nhưng transaction/model revision/entity/property postcondition không đạt yêu cầu; không được tự động retry khi chưa đọc lại model state",
            "TuSketchupAgent::TransactionVerificationError"
          ).merge(
            verification: verification,
            mutation_committed: verification[:committed] == true,
            retry_safe: false,
            model_state: after_state
          )
        end
      end

      result.merge(
        request_id: request_id,
        command: command,
        duration_ms: Response.elapsed_ms(started_at)
      )
    rescue StandardError => e
      Response.error(request_id, command, "INTERNAL_ERROR", e.message, e.class.name)
    end
  end

  # Module-level delegate for backward compatibility
  def self.dispatch(payload)
    Router.dispatch(payload)
  end
end
