# frozen_string_literal: true

module TuSketchupAgent
  module Handlers
    module Inspection
      extend self

      def register
        Router.register("get_entities") { |args| get_entities(args) }
        Router.register("get_entity_info") { |args| get_entity_info(args) }
        Router.register("get_bounding_box") { |args| get_bounding_box(args) }
      end

      def get_entities(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        requested_id = args["parent_id"] || args["persistent_id"] || args["entity_id"] || args["reference_id"]
        parent = nil
        parent_context = nil
        target_entities = model.active_entities

        if requested_id
          parent = if args["persistent_id"]
            Services::EntityService.find_entity_by_persistent_id(model, args["persistent_id"])
          elsif args["entity_id"]
            Services::EntityService.find_entity_by_id(model, args["entity_id"])
          elsif args["reference_id"]
            Services::EntityService.find_entity_by_persistent_id(model, args["reference_id"])
          elsif args["parent_id"]
            Services::EntityService.find_entity_by_persistent_id(model, args["parent_id"]) || Services::EntityService.find_entity_by_id(model, args["parent_id"])
          end

          raise ArgumentError, "Không tìm thấy parent entity với ID #{requested_id}" unless parent

          if parent.is_a?(Sketchup::ComponentInstance)
            target_entities = parent.definition.entities
            t = parent.transformation
            parent_context = {
              type: "component_definition",
              coordinate_space: "component_definition_local",
              definition_name: parent.definition.name,
              instance: Services::MetadataService.entity_metadata(parent),
              transformation: {
                origin_mm: [t.origin.x.to_mm.round(1), t.origin.y.to_mm.round(1), t.origin.z.to_mm.round(1)],
                xscale: t.xscale.round(4),
                yscale: t.yscale.round(4),
                zscale: t.zscale.round(4)
              }
            }
          elsif parent.respond_to?(:entities)
            target_entities = parent.entities
            t = parent.respond_to?(:transformation) ? parent.transformation : nil
            parent_context = {
              type: "group_container",
              coordinate_space: "group_container_local",
              parent: Services::MetadataService.entity_metadata(parent),
              transformation: t ? {
                origin_mm: [t.origin.x.to_mm.round(1), t.origin.y.to_mm.round(1), t.origin.z.to_mm.round(1)],
                xscale: t.xscale.round(4),
                yscale: t.yscale.round(4),
                zscale: t.zscale.round(4)
              } : nil
            }
          else
            raise ArgumentError, "Entity ID #{requested_id} không chứa danh sách entities con"
          end
        end

        type_filter = args["type_filter"].to_s.strip
        layer_filter = args["layer_filter"].to_s.strip
        name_filter = args["name_filter"].to_s.strip
        limit = (args["limit"] || 100).to_i.clamp(1, 1000)
        offset = (args["offset"] || 0).to_i
        offset = 0 if offset < 0

        all_list = target_entities.to_a

        filtered = all_list.select do |e|
          match = true

          if !type_filter.empty?
            class_name = e.class.name.sub("Sketchup::", "")
            match = false unless class_name.casecmp?(type_filter)
          end

          if match && !layer_filter.empty?
            layer_name = e.respond_to?(:layer) && e.layer ? e.layer.name : "Layer0"
            match = false unless layer_name.casecmp?(layer_filter)
          end

          if match && !name_filter.empty?
            name_str = e.respond_to?(:name) ? e.name.to_s : ""
            match = false unless name_str.downcase.include?(name_filter.downcase)
          end

          match
        end

        sliced = filtered.slice(offset, limit) || []

        items = sliced.map do |e|
          meta = Services::MetadataService.entity_metadata(e)
          bbox = e.respond_to?(:bounds) ? e.bounds : nil
          meta.merge(
            visible: e.respond_to?(:visible?) ? e.visible? : true,
            material: e.respond_to?(:material) && e.material ? e.material.name : nil,
            bounds_mm: bbox ? {
              width: bbox.width.to_mm.round(1),
              depth: bbox.height.to_mm.round(1),
              height: bbox.depth.to_mm.round(1),
              center: [bbox.center.x.to_mm.round(1), bbox.center.y.to_mm.round(1), bbox.center.z.to_mm.round(1)]
            } : nil
          )
        end

        is_root = model.active_path.nil? || model.active_path.empty?
        active_context = if is_root
          { type: "root", name: "Model Root" }
        else
          curr = model.active_path.last
          {
            type: curr.class.name.sub("Sketchup::", ""),
            name: curr.respond_to?(:name) ? curr.name : nil,
            persistent_id: curr.respond_to?(:persistent_id) ? curr.persistent_id : nil,
            depth: model.active_path.length
          }
        end

        {
          ok: true,
          total_count: filtered.length,
          returned_count: items.length,
          offset: offset,
          limit: limit,
          active_context: active_context,
          parent_context: parent_context,
          items: items
        }
      end

      def get_entity_info(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        entity = if args["persistent_id"]
          Services::EntityService.find_entity_by_persistent_id(model, args["persistent_id"])
        elsif args["entity_id"]
          Services::EntityService.find_entity_by_id(model, args["entity_id"])
        elsif args["reference_id"]
          Services::EntityService.find_entity_by_persistent_id(model, args["reference_id"])
        else
          raise ArgumentError, "Thiếu tham số persistent_id hoặc entity_id"
        end

        raise ArgumentError, "Không tìm thấy đối tượng hợp lệ với ID cung cấp" unless entity && entity.valid?

        meta = Services::MetadataService.entity_metadata(entity)
        bbox = entity.respond_to?(:bounds) ? entity.bounds : nil

        info = {
          ok: true,
          entity: meta,
          valid: entity.valid?,
          hidden: entity.respond_to?(:hidden?) ? entity.hidden? : false,
          locked: entity.respond_to?(:locked?) ? entity.locked? : false,
          material: entity.respond_to?(:material) && entity.material ? entity.material.name : nil
        }

        if bbox
          info[:bounds_mm] = {
            width: bbox.width.to_mm.round(1),
            depth: bbox.height.to_mm.round(1),
            height: bbox.depth.to_mm.round(1),
            center: [bbox.center.x.to_mm.round(1), bbox.center.y.to_mm.round(1), bbox.center.z.to_mm.round(1)],
            min: [bbox.min.x.to_mm.round(1), bbox.min.y.to_mm.round(1), bbox.min.z.to_mm.round(1)],
            max: [bbox.max.x.to_mm.round(1), bbox.max.y.to_mm.round(1), bbox.max.z.to_mm.round(1)]
          }
        end

        if entity.is_a?(Sketchup::Group)
          info[:children_count] = entity.entities.length
          t = entity.transformation
          info[:transformation] = {
            position_mm: [t.origin.x.to_mm.round(1), t.origin.y.to_mm.round(1), t.origin.z.to_mm.round(1)],
            xscale: t.xscale.round(4),
            yscale: t.yscale.round(4),
            zscale: t.zscale.round(4)
          }
        elsif entity.is_a?(Sketchup::ComponentInstance)
          info[:definition_name] = entity.definition.name
          info[:children_count] = entity.definition.entities.length
          t = entity.transformation
          info[:transformation] = {
            position_mm: [t.origin.x.to_mm.round(1), t.origin.y.to_mm.round(1), t.origin.z.to_mm.round(1)],
            xscale: t.xscale.round(4),
            yscale: t.yscale.round(4),
            zscale: t.zscale.round(4)
          }
        elsif entity.is_a?(Sketchup::Face)
          info[:area_mm2] = (entity.area * 25.4 * 25.4).round(1)
          info[:back_material] = entity.back_material ? entity.back_material.name : nil
          info[:normal] = [entity.normal.x.round(4), entity.normal.y.round(4), entity.normal.z.round(4)]
          info[:vertices_count] = entity.vertices.length
        elsif entity.is_a?(Sketchup::Edge)
          info[:length_mm] = entity.length.to_mm.round(1)
          info[:start_point_mm] = [entity.start.position.x.to_mm.round(1), entity.start.position.y.to_mm.round(1), entity.start.position.z.to_mm.round(1)]
          info[:end_point_mm] = [entity.end.position.x.to_mm.round(1), entity.end.position.y.to_mm.round(1), entity.end.position.z.to_mm.round(1)]
        end

        info
      end

      def get_bounding_box(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        items = []
        if args["persistent_ids"]
          Array(args["persistent_ids"]).each { |id| items << [:pid, id] }
        elsif args["entity_ids"]
          Array(args["entity_ids"]).each { |id| items << [:eid, id] }
        elsif args["persistent_id"]
          items << [:pid, args["persistent_id"]]
        elsif args["entity_id"]
          items << [:eid, args["entity_id"]]
        elsif args["reference_ids"]
          Array(args["reference_ids"]).each { |id| items << [:ref, id] }
        elsif args["reference_id"]
          items << [:ref, args["reference_id"]]
        end

        raise ArgumentError, "Cần danh sách ID đối tượng không rỗng" if items.empty?
        raise ArgumentError, "Tối đa 1000 đối tượng mỗi request (nhận #{items.length})" if items.length > 1000

        combined_bb = Geom::BoundingBox.new
        found_count = 0
        missing_ids = []

        items.each do |type, id|
          e = case type
          when :pid then Services::EntityService.find_entity_by_persistent_id(model, id)
          when :eid then Services::EntityService.find_entity_by_id(model, id)
          when :ref then Services::EntityService.find_entity_by_persistent_id(model, id)
          end

          if e && e.valid? && e.respond_to?(:bounds)
            combined_bb.add(e.bounds)
            found_count += 1
          else
            missing_ids << id
          end
        end

        raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ trong danh sách ID cung cấp" if found_count == 0

        {
          ok: true,
          found_count: found_count,
          missing_ids: missing_ids,
          bounds_mm: {
            width: combined_bb.width.to_mm.round(1),
            depth: combined_bb.height.to_mm.round(1),
            height: combined_bb.depth.to_mm.round(1),
            center: [combined_bb.center.x.to_mm.round(1), combined_bb.center.y.to_mm.round(1), combined_bb.center.z.to_mm.round(1)],
            min: [combined_bb.min.x.to_mm.round(1), combined_bb.min.y.to_mm.round(1), combined_bb.min.z.to_mm.round(1)],
            max: [combined_bb.max.x.to_mm.round(1), combined_bb.max.y.to_mm.round(1), combined_bb.max.z.to_mm.round(1)]
          }
        }
      end
    end
  end

  # Module-level delegates for backward compatibility
  def self.get_entities(args)
    Handlers::Inspection.get_entities(args)
  end

  def self.get_entity_info(args)
    Handlers::Inspection.get_entity_info(args)
  end

  def self.get_bounding_box(args)
    Handlers::Inspection.get_bounding_box(args)
  end
end
