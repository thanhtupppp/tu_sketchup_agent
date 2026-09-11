# frozen_string_literal: true

module TuSketchupAgent
  module Handlers
    module Attributes
      extend self

      def register
        Router.register("get_entity_attributes") { |args| get_entity_attributes(args) }
        Router.register("set_entity_attributes") { |args| set_entity_attributes(args) }
        Router.register("delete_entity_attributes") { |args| delete_entity_attributes(args) }
      end

      def get_entity_attributes(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        target = args["persistent_id"] || args["entity_id"] || args["id"]
        raise ArgumentError, "Cần cung cấp ID đối tượng (persistent_id hoặc entity_id)" unless target

        entity = if args["persistent_id"]
          Services::EntityService.find_entity_by_persistent_id(model, args["persistent_id"])
        elsif args["entity_id"]
          Services::EntityService.find_entity_by_id(model, args["entity_id"])
        else
          Services::EntityService.find_entity(model, target)
        end
        raise ArgumentError, "Không tìm thấy đối tượng với ID #{target}" unless entity

        dict_filter = args["dictionary_name"].to_s.strip
        dictionaries = {}

        if !dict_filter.empty?
          dict = entity.attribute_dictionary(dict_filter, false)
          if dict
            d_hash = {}
            dict.each { |k, v| d_hash[k] = v }
            dictionaries[dict_filter] = d_hash
          end
        elsif entity.attribute_dictionaries
          entity.attribute_dictionaries.each do |d|
            d_hash = {}
            d.each { |k, v| d_hash[k] = v }
            dictionaries[d.name] = d_hash
          end
        end

        {
          ok: true,
          entity: Services::MetadataService.entity_metadata(entity),
          dictionary_count: dictionaries.keys.length,
          dictionaries: dictionaries,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def set_entity_attributes(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        dict_name = args["dictionary_name"].to_s.strip
        raise ArgumentError, "Thiếu tham số dictionary_name" if dict_name.empty?

        attrs = args["attributes"]
        raise ArgumentError, "attributes phải là một Hash key-value" unless attrs.is_a?(Hash) && !attrs.empty?

        entities, missing_ids = Services::EntityService.resolve_entities_from_args(model, args)
        raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để gán thuộc tính" if entities.empty?

        entities.each do |e|
          Services::EntityService.validate_group_or_component!(e)
        end

        Operation.with_operation(model, "AI - Set Entity Attributes") do
          entities.each do |e|
            attrs.each do |k, v|
              e.set_attribute(dict_name, k.to_s, v)
            end
          end
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "set_entity_attributes",
          updated_count: entities.length,
          dictionary_name: dict_name,
          attributes_written: attrs.keys,
          missing_ids: missing_ids,
          entities: entities.map { |e| Services::MetadataService.entity_metadata(e) },
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def delete_entity_attributes(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        dict_name = args["dictionary_name"].to_s.strip
        raise ArgumentError, "Thiếu tham số dictionary_name" if dict_name.empty?

        keys = args["keys"].is_a?(Array) ? args["keys"].map(&:to_s) : nil

        entities, missing_ids = Services::EntityService.resolve_entities_from_args(model, args)
        raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để xóa thuộc tính" if entities.empty?

        entities.each do |e|
          Services::EntityService.validate_group_or_component!(e)
        end

        Operation.with_operation(model, "AI - Delete Entity Attributes") do
          entities.each do |e|
            if keys && !keys.empty?
              dict = e.attribute_dictionary(dict_name, false)
              if dict
                keys.each { |k| dict.delete_key(k) }
              end
            elsif e.attribute_dictionaries
              e.attribute_dictionaries.delete(dict_name)
            end
          end
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "delete_entity_attributes",
          updated_count: entities.length,
          dictionary_name: dict_name,
          deleted_keys: keys,
          deleted_entire_dictionary: keys.nil? || keys.empty?,
          missing_ids: missing_ids,
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end
    end
  end

  # Module-level delegates for backward compatibility
  def self.get_entity_attributes(args)
    Handlers::Attributes.get_entity_attributes(args)
  end

  def self.set_entity_attributes(args)
    Handlers::Attributes.set_entity_attributes(args)
  end

  def self.delete_entity_attributes(args)
    Handlers::Attributes.delete_entity_attributes(args)
  end
end
