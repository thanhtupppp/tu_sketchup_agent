# frozen_string_literal: true

require_relative "plan"
require_relative "model_state"
require_relative "../services/entity_service"

module TuSketchupAgent
  module PlanPreflight
    extend self

    CONTRACT_VERSION = 1

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

      unless plan_validation[:valid]
        return result(false, plan_validation, checks, errors, warnings, model_state(model))
      end

      unless model
        errors << "Không có model đang mở"
        return result(false, plan_validation, checks, errors, warnings, nil)
      end

      state = model_state(model)
      steps = Plan.normalize(plan)[:steps]
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
          errors << "#{prefix}.arguments thiếu tham số bắt buộc: #{key}" if value.nil? || (value.respond_to?(:empty?) && value.empty?)
        end

        if ENTITY_COMMANDS.include?(command)
          ids = extract_entity_targets(args)
          if ids.empty?
            errors << "#{prefix}.arguments thiếu ID entity cho command #{command}"
          else
            missing = ids.reject { |id| Services::EntityService.find_entity(model, id) }
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
          entity_dependency_checked: ENTITY_COMMANDS.include?(command)
        }
      end

      result(errors.empty?, plan_validation, checks, errors, warnings, state)
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

    def result(valid, plan_validation, checks, errors, warnings, state)
      {
        valid: valid,
        contract_version: CONTRACT_VERSION,
        plan_validation: plan_validation,
        checks: checks,
        errors: errors,
        warnings: warnings,
        model_state: state
      }
    end
  end
end
