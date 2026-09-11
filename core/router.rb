# frozen_string_literal: true

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
