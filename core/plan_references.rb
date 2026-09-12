# frozen_string_literal: true

module TuSketchupAgent
  module PlanReferences
    extend self

    PREFIX = "$ref:".freeze

    def references(value)
      found = []
      walk(value) do |ref|
        found << ref
      end
      found.uniq
    end

    def parse(reference)
      raw = reference.to_s
      return nil unless raw.start_with?(PREFIX)

      path = raw.delete_prefix(PREFIX).strip
      return nil if path.empty?

      parts = path.split(".")
      return nil if parts.empty? || parts.any? { |part| part.empty? }

      {
        raw: raw,
        step_id: parts.shift,
        path: parts
      }
    end

    def validate_references(steps)
      errors = []
      warnings = []
      index_by_step = {}

      Array(steps).each_with_index do |step, index|
        step_id = value(step, "step_id").to_s
        index_by_step[step_id] = index unless step_id.empty? || index_by_step.key?(step_id)
      end

      Array(steps).each_with_index do |step, index|
        refs = references(value(step, "arguments"))
        refs.each do |raw|
          parsed = parse(raw)
          unless parsed
            errors << "steps[#{index}] reference không hợp lệ: #{raw}"
            next
          end

          target_index = index_by_step[parsed[:step_id]]
          if target_index.nil?
            errors << "steps[#{index}] reference không tìm thấy step: #{parsed[:step_id]}"
          elsif target_index >= index
            errors << "steps[#{index}] reference phải trỏ tới step trước: #{parsed[:step_id]}"
          elsif parsed[:path].empty?
            errors << "steps[#{index}] reference phải có output path: #{raw}"
          end
        end
      end

      { valid: errors.empty?, errors: errors, warnings: warnings }
    end

    def resolve(value, outputs)
      case value
      when Hash
        value.each_with_object({}) do |(key, item), out|
          out[key] = resolve(item, outputs)
        end
      when Array
        value.map { |item| resolve(item, outputs) }
      when String
        parsed = parse(value)
        return value unless parsed

        cursor = outputs[parsed[:step_id].to_s]
        raise KeyError, "Không tìm thấy output của step: #{parsed[:step_id]}" unless cursor

        parsed[:path].each do |part|
          cursor = fetch_path(cursor, part)
        end
        deep_dup(cursor)
      else
        value
      end
    end

    private

    def walk(value, &block)
      case value
      when Hash
        value.each_value { |item| walk(item, &block) }
      when Array
        value.each { |item| walk(item, &block) }
      when String
        yield value if value.start_with?(PREFIX)
      end
    end

    def fetch_path(value, part)
      if value.is_a?(Hash)
        value.key?(part) ? value[part] : value[part.to_sym]
      elsif value.is_a?(Array) && part.match?(/\A\d+\z/)
        value[part.to_i]
      else
        nil
      end.tap do |result|
        raise KeyError, "Không tìm thấy output path: #{part}" if result.nil?
      end
    end

    def deep_dup(value)
      Marshal.load(Marshal.dump(value))
    rescue StandardError
      value
    end

    def value(hash, key)
      hash[key] || hash[key.to_sym]
    end
  end
end
