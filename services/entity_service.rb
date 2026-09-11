# frozen_string_literal: true

module TuSketchupAgent
  module Services
    module EntityService
      extend self

      def validate_dimension!(value, name)
        raise ArgumentError, "#{name} phải lớn hơn 0" unless value > 0
        raise ArgumentError, "#{name} (#{value} mm) vượt giới hạn tối đa #{TuSketchupAgent::MAX_DIMENSION_MM} mm" if value > TuSketchupAgent::MAX_DIMENSION_MM
      end

      def validate_group_or_component!(entity)
        unless entity.is_a?(Sketchup::Group) || entity.is_a?(Sketchup::ComponentInstance)
          eid = entity.respond_to?(:persistent_id) ? entity.persistent_id : (entity.respond_to?(:entityID) ? entity.entityID : "unknown")
          raise ArgumentError, "Đối tượng ID #{eid} có kiểu #{entity.class.name} không được hỗ trợ. Chỉ hỗ trợ thao tác trên Sketchup::Group hoặc Sketchup::ComponentInstance."
        end
      end

      def find_entity_by_persistent_id(model, id)
        return nil unless model && id
        return nil if id.to_s.strip.empty?
        int_id = Integer(id)
        return nil if int_id <= 0

        entity = model.find_entity_by_persistent_id(int_id) if model.respond_to?(:find_entity_by_persistent_id)
        return nil unless entity
        return nil if entity.respond_to?(:valid?) && !entity.valid?

        entity
      rescue ArgumentError, TypeError
        nil
      end

      def find_entity_recursive(entities, entity_id)
        return nil unless entities
        entities.each do |entity|
          return entity if entity.respond_to?(:entityID) && entity.entityID == entity_id
          if entity.is_a?(Sketchup::Group)
            found = find_entity_recursive(entity.entities, entity_id)
            return found if found
          elsif entity.is_a?(Sketchup::ComponentInstance)
            found = find_entity_recursive(entity.definition.entities, entity_id)
            return found if found
          end
        end
        nil
      end

      def find_entity_by_id(model, id)
        return nil unless model && id
        return nil if id.to_s.strip.empty?
        int_id = Integer(id)
        return nil if int_id <= 0

        entity = model.find_entity_by_id(int_id) if model.respond_to?(:find_entity_by_id)
        entity = find_entity_recursive(model.entities, int_id) if entity.nil?
        entity = find_entity_recursive(model.active_entities, int_id) if entity.nil? && model.respond_to?(:active_entities) && model.active_entities != model.entities
        return nil unless entity
        return nil if entity.respond_to?(:valid?) && !entity.valid?

        entity
      rescue ArgumentError, TypeError
        nil
      end

      def find_entity(model, target)
        return nil unless model && target

        if target.is_a?(Hash)
          if target["persistent_id"]
            find_entity_by_persistent_id(model, target["persistent_id"])
          elsif target["entity_id"]
            find_entity_by_id(model, target["entity_id"])
          elsif target["reference_id"]
            find_entity_by_persistent_id(model, target["reference_id"])
          elsif target["parent_id"]
            find_entity_by_persistent_id(model, target["parent_id"]) || find_entity_by_id(model, target["parent_id"])
          elsif target["id"]
            find_entity_by_persistent_id(model, target["id"]) || find_entity_by_id(model, target["id"])
          end
        else
          find_entity_by_persistent_id(model, target) || find_entity_by_id(model, target)
        end
      end

      def resolve_entities_from_args(model, args)
        raw_ids = []
        if args["ids"].is_a?(Array)
          raw_ids = args["ids"]
        elsif args["persistent_ids"].is_a?(Array)
          raw_ids = args["persistent_ids"].map { |id| { "persistent_id" => id } }
        elsif args["entity_ids"].is_a?(Array)
          raw_ids = args["entity_ids"].map { |id| { "entity_id" => id } }
        elsif args["id"]
          raw_ids = [args["id"]]
        elsif args["persistent_id"]
          raw_ids = [{ "persistent_id" => args["persistent_id"] }]
        elsif args["entity_id"]
          raw_ids = [{ "entity_id" => args["entity_id"] }]
        end

        raise ArgumentError, "Cần cung cấp ít nhất một ID đối tượng (ids, persistent_ids, entity_ids hoặc id)" if raw_ids.empty?

        entities = []
        missing_ids = []

        raw_ids.each do |item|
          entity = find_entity(model, item)
          if entity && entity.respond_to?(:valid?) && entity.valid?
            entities << entity
          else
            missing_ids << (item.is_a?(Hash) ? (item["persistent_id"] || item["entity_id"] || item["id"]) : item)
          end
        end

        [entities, missing_ids]
      end
    end
  end

  # Module-level delegates for backward compatibility
  def self.validate_dimension!(value, name)
    Services::EntityService.validate_dimension!(value, name)
  end

  def self.validate_group_or_component!(entity)
    Services::EntityService.validate_group_or_component!(entity)
  end

  def self.find_entity_by_persistent_id(model, id)
    Services::EntityService.find_entity_by_persistent_id(model, id)
  end

  def self.find_entity_recursive(entities, entity_id)
    Services::EntityService.find_entity_recursive(entities, entity_id)
  end

  def self.find_entity_by_id(model, id)
    Services::EntityService.find_entity_by_id(model, id)
  end

  def self.find_entity(model, target)
    Services::EntityService.find_entity(model, target)
  end

  def self.resolve_entities_from_args(model, args)
    Services::EntityService.resolve_entities_from_args(model, args)
  end
end
