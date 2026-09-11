# frozen_string_literal: true

module TuSketchupAgent
  module Handlers
    module Transform
      extend self

      def register
        Router.register("move") { |args| move_entities(args) }
        Router.register("copy") { |args| copy_entities(args) }
        Router.register("rotate") { |args| rotate_entities(args) }
        Router.register("scale") { |args| scale_entities(args) }
        Router.register("delete") { |args| delete_entities(args) }
        Router.register("group") { |args| group_entities(args) }
        Router.register("ungroup") { |args| ungroup_entities(args) }
      end

      def move_entities(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        dx = Float(args["dx"] || 0.0)
        dy = Float(args["dy"] || 0.0)
        dz = Float(args["dz"] || 0.0)

        vec = Geom::Vector3d.new(dx.mm, dy.mm, dz.mm)
        raise ArgumentError, "Vector dịch chuyển (dx, dy, dz) phải khác 0" if vec.length < 0.0001

        entities, missing_ids = Services::EntityService.resolve_entities_from_args(model, args)
        raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để di chuyển" if entities.empty?

        t = Geom::Transformation.translation(vec)

        Operation.with_operation(model, "AI - Move Entities") do
          entities.each do |entity|
            if entity.respond_to?(:transform!)
              entity.transform!(t)
            elsif entity.parent && entity.parent.respond_to?(:entities)
              entity.parent.entities.transform_entities(t, [entity])
            else
              model.active_entities.transform_entities(t, [entity])
            end
          end
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "move",
          moved_count: entities.length,
          missing_ids: missing_ids,
          vector_mm: [dx, dy, dz],
          entities: entities.map { |e| Services::MetadataService.entity_metadata(e) },
          bounds_mm: Services::TransformationService.calculate_bounds_mm(entities),
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision
        }
      end

      def copy_entities(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        dx = Float(args["dx"] || 0.0)
        dy = Float(args["dy"] || 0.0)
        dz = Float(args["dz"] || 0.0)

        vec = Geom::Vector3d.new(dx.mm, dy.mm, dz.mm)
        t = Geom::Transformation.translation(vec)

        entities, missing_ids = Services::EntityService.resolve_entities_from_args(model, args)
        raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để sao chép" if entities.empty?

        new_entities = []

        Operation.with_operation(model, "AI - Copy Entities") do
          entities.each do |entity|
            if entity.is_a?(Sketchup::Group)
              copy_grp = entity.copy
              copy_grp.transform!(t) unless vec.length < 0.0001
              new_entities << copy_grp
            elsif entity.is_a?(Sketchup::ComponentInstance)
              container = entity.parent.is_a?(Sketchup::ComponentDefinition) ? entity.parent.entities : model.active_entities
              copy_inst = container.add_instance(entity.definition, entity.transformation * t)
              new_entities << copy_inst
            elsif entity.parent && entity.parent.respond_to?(:entities)
              copy_grp = model.active_entities.add_group([entity])
              dupe = copy_grp.copy
              dupe.transform!(t) unless vec.length < 0.0001
              new_entities.concat(dupe.explode.grep(Sketchup::Drawingelement))
              copy_grp.explode
            end
          end
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "copy",
          copied_count: new_entities.length,
          missing_ids: missing_ids,
          vector_mm: [dx, dy, dz],
          entities: new_entities.map { |e| Services::MetadataService.entity_metadata(e) },
          bounds_mm: Services::TransformationService.calculate_bounds_mm(new_entities),
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision
        }
      end

      def rotate_entities(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        angle_deg = Float(args.fetch("angle_degrees"))
        raise ArgumentError, "Góc quay (angle_degrees) phải khác 0" if angle_deg.abs < 0.001

        axis_arg = args["axis"] || "z"
        axis_vec = case axis_arg.to_s.downcase
        when "x" then Geom::Vector3d.new(1, 0, 0)
        when "y" then Geom::Vector3d.new(0, 1, 0)
        when "z" then Geom::Vector3d.new(0, 0, 1)
        else
          if axis_arg.is_a?(Array) && axis_arg.length == 3
            Geom::Vector3d.new(Float(axis_arg[0]), Float(axis_arg[1]), Float(axis_arg[2]))
          else
            raise ArgumentError, "axis phải là 'x', 'y', 'z' hoặc mảng 3 phần tử [ax, ay, az]"
          end
        end
        raise ArgumentError, "Vector trục quay không hợp lệ (độ dài bằng 0)" if axis_vec.length < 0.0001
        axis_vec.normalize!

        entities, missing_ids = Services::EntityService.resolve_entities_from_args(model, args)
        raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để xoay" if entities.empty?

        combined_bb = Geom::BoundingBox.new
        entities.each { |e| combined_bb.add(e.bounds) if e.respond_to?(:bounds) }

        origin_pt = if args["origin"].is_a?(Array) && args["origin"].length == 3
          Geom::Point3d.new(Float(args["origin"][0]).mm, Float(args["origin"][1]).mm, Float(args["origin"][2]).mm)
        else
          combined_bb.center
        end

        t = Geom::Transformation.rotation(origin_pt, axis_vec, angle_deg.degrees)

        Operation.with_operation(model, "AI - Rotate Entities") do
          entities.each do |entity|
            if entity.respond_to?(:transform!)
              entity.transform!(t)
            elsif entity.parent && entity.parent.respond_to?(:entities)
              entity.parent.entities.transform_entities(t, [entity])
            else
              model.active_entities.transform_entities(t, [entity])
            end
          end
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "rotate",
          rotated_count: entities.length,
          missing_ids: missing_ids,
          axis: axis_arg,
          angle_degrees: angle_deg,
          origin_mm: [origin_pt.x.to_mm.round(1), origin_pt.y.to_mm.round(1), origin_pt.z.to_mm.round(1)],
          entities: entities.map { |e| Services::MetadataService.entity_metadata(e) },
          bounds_mm: Services::TransformationService.calculate_bounds_mm(entities),
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision
        }
      end

      def scale_entities(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        x_scale = Float(args["x_scale"] || args["scale"] || 1.0)
        y_scale = Float(args["y_scale"] || args["scale"] || 1.0)
        z_scale = Float(args["z_scale"] || args["scale"] || 1.0)

        raise ArgumentError, "Tỷ lệ scale x_scale, y_scale, z_scale phải khác 0" if x_scale == 0 || y_scale == 0 || z_scale == 0

        entities, missing_ids = Services::EntityService.resolve_entities_from_args(model, args)
        raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để scale" if entities.empty?

        combined_bb = Geom::BoundingBox.new
        entities.each { |e| combined_bb.add(e.bounds) if e.respond_to?(:bounds) }

        origin_pt = if args["origin"].is_a?(Array) && args["origin"].length == 3
          Geom::Point3d.new(Float(args["origin"][0]).mm, Float(args["origin"][1]).mm, Float(args["origin"][2]).mm)
        else
          combined_bb.center
        end

        t = Geom::Transformation.scaling(origin_pt, x_scale, y_scale, z_scale)

        Operation.with_operation(model, "AI - Scale Entities") do
          entities.each do |entity|
            if entity.respond_to?(:transform!)
              entity.transform!(t)
            elsif entity.parent && entity.parent.respond_to?(:entities)
              entity.parent.entities.transform_entities(t, [entity])
            else
              model.active_entities.transform_entities(t, [entity])
            end
          end
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "scale",
          scaled_count: entities.length,
          missing_ids: missing_ids,
          scale: [x_scale, y_scale, z_scale],
          origin_mm: [origin_pt.x.to_mm.round(1), origin_pt.y.to_mm.round(1), origin_pt.z.to_mm.round(1)],
          entities: entities.map { |e| Services::MetadataService.entity_metadata(e) },
          bounds_mm: Services::TransformationService.calculate_bounds_mm(entities),
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision
        }
      end

      def delete_entities(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        entities, missing_ids = Services::EntityService.resolve_entities_from_args(model, args)
        raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để xóa" if entities.empty?

        deleted_items = []
        Operation.with_operation(model, "AI - Delete Entities") do
          entities.each do |entity|
            meta = Services::MetadataService.entity_metadata(entity)
            if entity.respond_to?(:erase!)
              entity.erase!
              deleted_items << meta
            end
          end
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "delete",
          deleted_count: deleted_items.length,
          missing_ids: missing_ids,
          entities: deleted_items,
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision
        }
      end

      def group_entities(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        name = args["name"].to_s
        entities, missing_ids = Services::EntityService.resolve_entities_from_args(model, args)
        raise ArgumentError, "Cần ít nhất một đối tượng hợp lệ để tạo nhóm" if entities.empty?

        # Verify all entities share the same parent container
        parents = entities.map { |e| e.respond_to?(:parent) ? e.parent : nil }.uniq
        if parents.length > 1
          parent_names = parents.map { |p| p.is_a?(Sketchup::Model) ? "Model root" : (p.respond_to?(:name) ? p.name : p.class.name) }
          raise ArgumentError, "Tất cả đối tượng phải cùng chung một container mới nhóm được. Hiện có #{parents.length} containers khác nhau: #{parent_names.join(', ')}"
        end

        # Use the parent's entities collection, not necessarily model.active_entities
        target_entities_collection = if parents.first.is_a?(Sketchup::Model)
          parents.first.active_entities
        elsif parents.first.respond_to?(:entities)
          parents.first.entities
        else
          model.active_entities
        end

        group = nil
        Operation.with_operation(model, "AI - Group Entities") do
          group = target_entities_collection.add_group(entities)
          group.name = name unless name.empty?
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "group",
          group: Services::MetadataService.entity_metadata(group),
          children_count: entities.length,
          missing_ids: missing_ids,
          bounds_mm: group.bounds ? {
            width: group.bounds.width.to_mm.round(1),
            depth: group.bounds.height.to_mm.round(1),
            height: group.bounds.depth.to_mm.round(1),
            center: [group.bounds.center.x.to_mm.round(1), group.bounds.center.y.to_mm.round(1), group.bounds.center.z.to_mm.round(1)]
          } : nil,
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision
        }
      end

      def ungroup_entities(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        target = args["id"] || args["persistent_id"] || args["entity_id"]
        raise ArgumentError, "Thiếu tham số id/persistent_id của group cần rã" unless target

        entity = Services::EntityService.find_entity(model, target)
        raise ArgumentError, "Không tìm thấy group với ID cung cấp" unless entity && entity.valid?
        raise ArgumentError, "Đối tượng ID #{target} không phải là Sketchup::Group (loại: #{entity.class.name})" unless entity.is_a?(Sketchup::Group)

        exploded_entities = []
        Operation.with_operation(model, "AI - Ungroup Entities") do
          exploded_entities = entity.explode
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "ungroup",
          exploded_count: exploded_entities.length,
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision
        }
      end
    end
  end

  # Module-level delegates for backward compatibility
  def self.move_entities(args)
    Handlers::Transform.move_entities(args)
  end

  def self.copy_entities(args)
    Handlers::Transform.copy_entities(args)
  end

  def self.rotate_entities(args)
    Handlers::Transform.rotate_entities(args)
  end

  def self.scale_entities(args)
    Handlers::Transform.scale_entities(args)
  end

  def self.delete_entities(args)
    Handlers::Transform.delete_entities(args)
  end

  def self.group_entities(args)
    Handlers::Transform.group_entities(args)
  end

  def self.ungroup_entities(args)
    Handlers::Transform.ungroup_entities(args)
  end
end
