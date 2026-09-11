# frozen_string_literal: true

module TuSketchupAgent
  module Verification
    extend self

    CONTRACT_VERSION = 4
    DIMENSION_TOLERANCE_MM = 1.0

    def entity_target?(result)
      result.is_a?(Hash) && (
        result[:entity].is_a?(Hash) ||
        result[:entities].is_a?(Array) ||
        result[:group].is_a?(Hash)
      )
    end

    def entity_metadata(result)
      return [] unless result.is_a?(Hash)
      items = []
      items << result[:entity] if result[:entity].is_a?(Hash)
      items.concat(result[:entities].select { |item| item.is_a?(Hash) }) if result[:entities].is_a?(Array)
      items << result[:group] if result[:group].is_a?(Hash)
      items
    end

    def verify_entities(model, result, deleted: false)
      targets = entity_metadata(result)
      return { attempted: false, verified: true, reason: "no_entity_metadata" } if targets.empty?

      checks = targets.map do |metadata|
        entity = Services::EntityService.find_entity(model, metadata)
        exists = !entity.nil? && (!entity.respond_to?(:valid?) || entity.valid?)
        valid_type = if exists && metadata[:type]
          entity.class.name.sub("Sketchup::", "") == metadata[:type].to_s
        else
          true
        end
        expected_exists = !deleted
        {
          persistent_id: metadata[:persistent_id],
          entity_id: metadata[:entity_id],
          expected_exists: expected_exists,
          exists: exists,
          valid: deleted ? !exists : (exists && valid_type),
          type_match: valid_type,
          type: metadata[:type]
        }
      end

      {
        attempted: true,
        verified: checks.all? { |check| check[:valid] },
        expected: deleted ? "entities_absent" : "entities_present",
        checked_count: checks.length,
        entities: checks
      }
    end

    def nearly_equal?(actual, expected, tolerance = DIMENSION_TOLERANCE_MM)
      (actual.to_f - expected.to_f).abs <= tolerance
    end

    def vector_nearly_equal?(actual, expected, tolerance = DIMENSION_TOLERANCE_MM)
      return false unless actual.is_a?(Array) && expected.is_a?(Array) && actual.length == 3 && expected.length == 3
      actual.zip(expected).all? { |a, e| nearly_equal?(a, e, tolerance) }
    end

    def bounds_center(bounds)
      return nil unless bounds.is_a?(Hash) && bounds[:center].is_a?(Array)
      bounds[:center].map(&:to_f)
    end

    def verify_bounds(result, entity)
      return { attempted: false, verified: true, reason: "no_bounds_expectation" } unless entity.respond_to?(:bounds)

      expected = case result[:operation].to_s
      when "create_box"
        dimensions = result[:dimensions_mm]
        dimensions.is_a?(Hash) ? {
          width_mm: dimensions[:width],
          depth_mm: dimensions[:depth],
          height_mm: dimensions[:height]
        } : nil
      when "create_cylinder"
        {
          width_mm: result[:radius_mm].to_f * 2.0,
          depth_mm: result[:radius_mm].to_f * 2.0,
          height_mm: result[:height_mm]
        }
      else
        nil
      end
      return { attempted: false, verified: true, reason: "unsupported_bounds_operation" } unless expected

      bounds = entity.bounds
      actual = {
        width_mm: bounds.width.to_mm,
        depth_mm: bounds.height.to_mm,
        height_mm: bounds.depth.to_mm
      }
      checks = {
        width_mm: expected[:width_mm].nil? || nearly_equal?(actual[:width_mm], expected[:width_mm]),
        depth_mm: expected[:depth_mm].nil? || nearly_equal?(actual[:depth_mm], expected[:depth_mm]),
        height_mm: expected[:height_mm].nil? || nearly_equal?(actual[:height_mm], expected[:height_mm])
      }
      {
        attempted: true,
        verified: checks.values.all?,
        tolerance_mm: DIMENSION_TOLERANCE_MM,
        expected_mm: expected,
        actual_mm: actual,
        checks: checks
      }
    end

    def verify_transform(result)
      operation = result[:operation].to_s
      return { attempted: false, verified: true, reason: "not_transform_operation" } unless %w[move copy rotate scale].include?(operation)

      before = bounds_center(result[:before_bounds_mm])
      after = bounds_center(result[:bounds_mm])
      return { attempted: false, verified: true, reason: "transform_snapshot_unavailable" } unless before && after

      expected = case operation
      when "move", "copy"
        vector = result[:vector_mm]
        vector.is_a?(Array) && vector.length == 3 ? before.zip(vector.map(&:to_f)).map { |a, v| a + v } : nil
      when "scale"
        origin = result[:origin_mm]
        scale = result[:scale]
        if origin.is_a?(Array) && origin.length == 3 && scale.is_a?(Array) && scale.length == 3
          origin.map(&:to_f).zip(before, scale.map(&:to_f)).map { |o, b, s| o + ((b - o) * s) }
        end
      when "rotate"
        origin = result[:origin_mm]
        axis = result[:axis]
        angle = result[:angle_degrees]
        if origin.is_a?(Array) && origin.length == 3 && angle && axis
          o = origin.map(&:to_f)
          a = case axis.to_s.downcase
          when "x" then [1.0, 0.0, 0.0]
          when "y" then [0.0, 1.0, 0.0]
          when "z" then [0.0, 0.0, 1.0]
          else axis.is_a?(Array) && axis.length == 3 ? axis.map(&:to_f) : nil
          end
          if a
            length = Math.sqrt(a.sum { |v| v * v })
            if length > 0.000001
              a = a.map { |v| v / length }
              v = before.zip(o).map { |b, ov| b - ov }
              radians = angle.to_f * Math::PI / 180.0
              c = Math.cos(radians)
              s = Math.sin(radians)
              cross = [
                a[1] * v[2] - a[2] * v[1],
                a[2] * v[0] - a[0] * v[2],
                a[0] * v[1] - a[1] * v[0]
              ]
              dot = a.zip(v).sum { |av, vv| av * vv }
              o.zip(v).each_with_index.map do |(ov, vv), i|
                ov + vv * c + cross[i] * s + a[i] * dot * (1.0 - c)
              end
            end
          end
        end
      end

      return { attempted: false, verified: true, reason: "transform_expectation_unavailable" } unless expected

      {
        attempted: true,
        verified: vector_nearly_equal?(after, expected),
        tolerance_mm: DIMENSION_TOLERANCE_MM,
        operation: operation,
        before_center_mm: before,
        actual_center_mm: after,
        expected_center_mm: expected
      }
    rescue StandardError => e
      {
        attempted: true,
        verified: false,
        operation: operation,
        error: e.message
      }
    end

    def verify_material(result, entity, args)
      operation = result[:operation].to_s
      expected_name = if operation == "set_entity_material"
        args["material_name"] || args["name"]
      elsif operation == "clear_entity_material"
        nil
      elsif %w[create_box create_cylinder create_wall].include?(operation)
        result[:material]
      end
      return { attempted: false, verified: true, reason: "no_material_expectation" } if operation.empty? || (expected_name.nil? && operation != "clear_entity_material")

      actual_name = entity.respond_to?(:material) && entity.material ? entity.material.name.to_s : nil
      verified = if operation == "clear_entity_material"
        actual_name.nil?
      else
        actual_name == expected_name.to_s
      end
      {
        attempted: true,
        verified: verified,
        expected: expected_name,
        actual: actual_name
      }
    end

    def verify_attributes(result, entity, args)
      return { attempted: false, verified: true, reason: "not_attribute_operation" } unless result[:operation].to_s == "set_entity_attributes"
      dict_name = args["dictionary_name"].to_s
      expected = args["attributes"]
      return { attempted: false, verified: true, reason: "invalid_attribute_expectation" } unless expected.is_a?(Hash)

      dict = entity.attribute_dictionary(dict_name, false)
      checks = expected.each_with_object({}) do |(key, value), memo|
        actual = dict ? dict[key.to_s] : nil
        memo[key.to_s] = {
          expected: value,
          actual: actual,
          match: actual == value
        }
      end
      {
        attempted: true,
        verified: checks.values.all? { |check| check[:match] },
        dictionary_name: dict_name,
        attributes: checks
      }
    end

    def verify_properties(model, result, args)
      transform = verify_transform(result)
      return { attempted: true, verified: transform[:verified], transform: transform } if transform[:attempted]
      return { attempted: false, verified: true, reason: "no_property_postcondition" } unless entity_target?(result)
      return { attempted: false, verified: true, reason: "delete_has_entity_absence_check" } if result[:operation].to_s == "delete"

      metadata = entity_metadata(result)
      checks = metadata.map do |item|
        entity = Services::EntityService.find_entity(model, item)
        next { verified: false, reason: "entity_missing" } unless entity

        bounds = verify_bounds(result, entity)
        material = verify_material(result, entity, args || {})
        attributes = verify_attributes(result, entity, args || {})
        {
          persistent_id: item[:persistent_id],
          bounds: bounds,
          material: material,
          attributes: attributes,
          verified: bounds[:verified] && material[:verified] && attributes[:verified]
        }
      end

      {
        attempted: true,
        verified: checks.all? { |check| check[:verified] },
        checked_count: checks.length,
        entities: checks
      }
    end

    def contract(command:, before_state:, after_state:, transaction:, handler_ok:, result: nil, model: nil, args: {})
      revision_delta = after_state[:revision].to_i - before_state[:revision].to_i
      committed = transaction[:status].to_s == "committed"
      session_id_unchanged = before_state[:model_session_id].to_s == after_state[:model_session_id].to_s

      entity_verification = if result && model && entity_target?(result)
        verify_entities(model, result, deleted: command.to_s == "delete")
      else
        { attempted: false, verified: true, reason: "no_entity_postcondition" }
      end

      property_verification = if result && model && handler_ok == true
        verify_properties(model, result, args)
      else
        { attempted: false, verified: true, reason: "handler_not_successful" }
      end

      verified = handler_ok == true && committed && revision_delta == 1 && session_id_unchanged &&
        entity_verification[:verified] && property_verification[:verified]

      {
        verification_contract_version: CONTRACT_VERSION,
        requested: true,
        executed: true,
        committed: committed,
        verified: verified,
        command: command.to_s,
        transaction: transaction,
        model_state_transition: {
          before_revision: before_state[:revision],
          after_revision: after_state[:revision],
          revision_delta: revision_delta,
          session_id_unchanged: session_id_unchanged
        },
        entity_postcondition: entity_verification,
        property_postcondition: property_verification
      }
    end
  end
end
