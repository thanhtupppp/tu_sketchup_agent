# frozen_string_literal: true

require "json"

module TuSketchupAgent
  module Response
    extend self

    def elapsed_ms(started_at)
      ((Process.clock_gettime(Process::CLOCK_MONOTONIC) - started_at) * 1000).round(2)
    end

    def error(request_id, command, code, message, error_class = nil)
      {
        ok: false,
        request_id: request_id,
        command: command,
        error: {
          code: code,
          message: message,
          class: error_class
        }
      }
    end

    def write(socket, payload)
      body = JSON.generate(payload)
      socket.write("#{body.bytesize}\n")
      socket.write(body)
      socket.flush
    end
  end

  # Module-level delegates for backward compatibility
  def self.elapsed_ms(started_at)
    Response.elapsed_ms(started_at)
  end

  def self.response_error(request_id, command, code, message, error_class = nil)
    Response.error(request_id, command, code, message, error_class)
  end

  def self.write_response(socket, payload)
    Response.write(socket, payload)
  end
end
