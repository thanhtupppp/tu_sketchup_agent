# frozen_string_literal: true

module TuSketchupAgent
  module Verification
    extend self

    CONTRACT_VERSION = 2

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

      verified = checks.all? { |check| check[:valid] }
      {
        attempted: true,
        verified: verified,
        expected: deleted ? "entities_absent" : "entities_present",
        checked_count: checks.length,
        entities: checks
      }
    end

    def contract(command:, before_state:, after_state:, transaction:, handler_ok:, result: nil, model: nil)
      revision_delta = after_state[:revision].to_i - before_state[:revision].to_i
      committed = transaction[:status].to_s == "committed"

      entity_verification = if result && model && entity_target?(result)
        verify_entities(model, result, deleted: command.to_s == "delete")
      else
        { attempted: false, verified: true, reason: "no_entity_postcondition" }
      end

      verified = handler_ok == true && committed && revision_delta == 1 && entity_verification[:verified]

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
          session_id_unchanged: before_state[:model_session_id].to_s == after_state[:model_session_id].to_s
        },
        entity_postcondition: entity_verification
      }
    end
  end
end
