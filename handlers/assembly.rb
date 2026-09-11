# frozen_string_literal: true

module TuSketchupAgent
  module Handlers
    module Assembly
      extend self

      def register
        Router.register("place_component_instance") { |args| place_component_instance(args) }
      end

      def place_component_instance(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        name = (args["definition_name"] || args["name"]).to_s.strip
        raise ArgumentError, "Thiếu tham số definition_name" if name.empty?

        defn = model.definitions[name]
        raise ArgumentError, "Không tìm thấy ComponentDefinition có tên '#{name}' trong model" unless defn

        container = model.active_entities
        if args["parent_id"]
          parent_entity = Services::EntityService.find_entity_by_persistent_id(model, args["parent_id"]) || Services::EntityService.find_entity_by_id(model, args["parent_id"])
          raise ArgumentError, "Không tìm thấy parent entity với ID #{args['parent_id']}" unless parent_entity
          if parent_entity.is_a?(Sketchup::Group)
            container = parent_entity.entities
          elsif parent_entity.is_a?(Sketchup::ComponentInstance)
            container = parent_entity.definition.entities
          else
            raise ArgumentError, "Parent entity phải là Group hoặc ComponentInstance"
          end
        end

        transform = Services::TransformationService.build_transformation(args)
        inst_name = args["instance_name"].to_s.strip

        instance = nil
        Operation.with_operation(model, "AI - Place Component Instance") do
          instance = container.add_instance(defn, transform)
          instance.name = inst_name unless inst_name.empty?
          Operation.bump_model_revision
        end

        bbox = instance.bounds
        {
          ok: true,
          operation: "place_component_instance",
          definition_name: defn.name,
          instance: Services::MetadataService.entity_metadata(instance),
          position_mm: [bbox.center.x.to_mm.round(1), bbox.center.y.to_mm.round(1), bbox.center.z.to_mm.round(1)],
          bounds_mm: {
            width: bbox.width.to_mm.round(1),
            depth: bbox.height.to_mm.round(1),
            height: bbox.depth.to_mm.round(1)
          },
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end
    end
  end

  # Module-level delegates for backward compatibility
  def self.place_component_instance(args)
    Handlers::Assembly.place_component_instance(args)
  end
end
