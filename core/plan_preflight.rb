# frozen_string_literal: true

require_relative "plan"
require_relative "model_state"
require_relative "../services/entity_service"
require_relative "plan_references"

module TuSketchupAgent
  module PlanPreflight
    extend self

    CONTRACT_VERSION = 2

    REQUIRED_ARGS = {
      "create_box" => %w[width depth height],
      "create_cylinder" => %w[radius height],
      "create_wall" => %w[width depth height],
      "move" => [],
      "copy" => [],
      "rotate" => %w[angle_degrees],
      "scale" => [],
      "delete" => [],
      "group" => [],
      "ungroup" => [],
      "set_entity_material" => %w[material],
      "clear_entity_material" => [],
      "set_entity_attribute" => %w[key value],
      "create_component" => %w[name],
      "make_component_unique" => [],
      "place_component_instance" => [],
      "import_file" => %w[path],
      "create_layer" => %w[name],
      "set_entity_layer" => %w[layer],
      "set_layer_visibility" => %w[layer visible],
      "create_scene" => %w[name]
    }.freeze

    ENTITY_COMMANDS = %w[
      move copy rotate scale delete group ungroup
      set_entity_material clear_entity_material set_entity_attribute
      make_component_unique set_entity_layer
    ].freeze

    def validate(plan, model: Sketchup.active_model, router_commands: [])
      plan_validation = Plan.validate(plan, router_commands: router_commands)
      errors = Array(plan_validation[:errors]).dup
      warnings = Array(plan_validation[:warnings]).dup
      checks = []
      reference_validation = { valid: true, errors: [], warnings: [] }

      unless plan_validation[:valid]
        return result(false, plan_validation, checks, errors, warnings, model_state(model), reference_validation)
      end

      unless model
        errors << "Không có model đang mở"
        return result(false, plan_validation, checks, errors, warnings, nil, reference_validation)
      end

      steps = Plan.normalize(plan)[:steps]
      reference_validation = PlanReferences.validate_references(steps)
      errors.concat(reference_validation[:errors])
      warnings.concat(reference_validation[:warnings])

      state = model_state(model)
      seen_step_ids = {}

      steps.each_with_index do |step, index|
        step_id = step[:step_id].to_s
        command = step[:command].to_s
        args = step[:arguments].is_a?(Hash) ? step[:arguments] : {}
        prefix = "steps[#{index}]"

        if seen_step_ids.key?(step_id)
          errors << "#{prefix}.step_id trùng với step trước: #{step_id}"
        else
          seen_step_ids[step_id] = true
        end

        REQUIRED_ARGS.fetch(command, []).each do |key|
          value = args[key] || args[key.to_sym]
          if value.nil? || (value.respond_to?(:empty?) && value.empty?)
            if value.is_a?(String) && value.start_with?(PlanReferences::PREFIX)
              next
            end
            errors << "#{prefix}.arguments thiếu tham số bắt buộc: #{key}"
          end
        end

        if ENTITY_COMMANDS.include?(command)
          ids = extract_entity_targets(args)
          literal_ids, refs = ids.partition { |id| !id.is_a?(String) || !id.start_with?(PlanReferences::PREFIX) }
          unless refs.empty?
            checks << {
              step_index: index,
              step_id: step_id,
              command: command,
              required_arguments_checked: REQUIRED_ARGS.fetch(command, []),
              entity_dependency_checked: true,
              entity_dependencies: { literal_checked: literal_ids.length, references: PlanReferences.references(args) }
            }
          end

          if literal_ids.empty? && refs.empty?
            errors << "#{prefix}.arguments thiếu ID entity cho command #{command}"
          else
            missing = literal_ids.reject { |id| Services::EntityService.find_entity(model, id) }
            unless missing.empty?
              errors << "#{prefix} entity dependency không tồn tại: #{missing.map(&:to_s).join(', ')}"
            end
          end
        end

        checks << {
          step_index: index,
          step_id: step_id,
          command: command,
          required_arguments_checked: REQUIRED_ARGS.fetch(command, []),
          entity_dependency_checked: ENTITY_COMMANDS.include?(command),
          references: PlanReferences.references(args)
        }
      end

      result(errors.empty?, plan_validation, checks, errors, warnings, state, reference_validation)
    end

    private

    def extract_entity_targets(args)
      if args["ids"].is_a?(Array)
        args["ids"]
      elsif args["persistent_ids"].is_a?(Array)
        args["persistent_ids"].map { |id| { "persistent_id" => id } }
      elsif args["entity_ids"].is_a?(Array)
        args["entity_ids"].map { |id| { "entity_id" => id } }
      elsif args["id"]
        [args["id"]]
      elsif args["persistent_id"]
        [{ "persistent_id" => args["persistent_id"] }]
      elsif args["entity_id"]
        [{ "entity_id" => args["entity_id"] }]
      else
        []
      end
    end

    def model_state(model)
      model ? TuSketchupAgent::ModelState.state(model) : nil
    end

    def result(valid, plan_validation, checks, errors, warnings, state, reference_validation)
      {
        valid: valid,
        contract_version: CONTRACT_VERSION,
        plan_validation: plan_validation,
        checks: checks,
        reference_validation: reference_validation,
        errors: errors,
        warnings: warnings,
        model_state: state
      }
    end
  end
end
