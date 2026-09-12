# frozen_string_literal: true

require "digest"
require "json"

module TuSketchupAgent
  module Idempotency
    extend self

    CACHE_LIMIT = 256

    @entries = {}
    @order = []

    def canonical_payload(command, args)
      JSON.generate(
        {
          command: command.to_s,
          arguments: normalize(args)
        }
      )
    end

    def fingerprint(command, args)
      Digest::SHA256.hexdigest(canonical_payload(command, args))
    end

    def lookup(request_id, command, args, model_session_id)
      id = request_id.to_s
      return nil if id.empty?

      entry = @entries[id]
      return nil unless entry

      fp = fingerprint(command, args)
      unless entry[:fingerprint] == fp
        return {
          status: :conflict,
          error_code: "IDEMPOTENCY_KEY_REUSE",
          message: "request_id đã được sử dụng cho một request khác"
        }
      end

      unless entry[:model_session_id].to_s == model_session_id.to_s
        return {
          status: :conflict,
          error_code: "IDEMPOTENCY_SESSION_MISMATCH",
          message: "request_id thuộc một model session khác; không replay request cũ"
        }
      end

      touch(id)
      {
        status: :replay,
        response: deep_dup(entry[:response])
      }
    end

    def store(request_id, command, args, model_session_id, response)
      id = request_id.to_s
      return response if id.empty?

      @entries[id] = {
        fingerprint: fingerprint(command, args),
        model_session_id: model_session_id.to_s,
        response: deep_dup(response)
      }
      touch(id)
      trim!
      response
    end

    def clear!
      @entries.clear
      @order.clear
    end

    private

    def touch(id)
      @order.delete(id)
      @order << id
    end

    def trim!
      while @order.length > CACHE_LIMIT
        oldest = @order.shift
        @entries.delete(oldest)
      end
    end

    def normalize(value)
      case value
      when Hash
        value.keys.map(&:to_s).sort.each_with_object({}) do |key, out|
          original_key = value.keys.find { |k| k.to_s == key }
          out[key] = normalize(value[original_key])
        end
      when Array
        value.map { |item| normalize(item) }
      else
        value
      end
    end

    def deep_dup(value)
      JSON.parse(JSON.generate(value), symbolize_names: true)
    rescue StandardError
      value
    end
  end
end
