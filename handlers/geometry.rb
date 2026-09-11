# frozen_string_literal: true

module TuSketchupAgent
  module Handlers
    module Geometry
      extend self

      def register
        Router.register("create_box") { |args| create_box(args) }
        Router.register("create_cylinder") { |args| create_cylinder(args) }
        Router.register("create_wall") { |args| create_wall(args) }
      end

      def create_box(args)
        width = Float(args.fetch("width"))
        depth = Float(args.fetch("depth"))
        height = Float(args.fetch("height"))

        Services::EntityService.validate_dimension!(width, "width")
        Services::EntityService.validate_dimension!(depth, "depth")
        Services::EntityService.validate_dimension!(height, "height")

        x = Float(args["x"] || 0.0)
        y = Float(args["y"] || 0.0)
        z = Float(args["z"] || 0.0)
        name = args["name"].to_s
        material_name = args["material"].to_s

        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        group = nil
        Operation.with_operation(model, "AI - Create Box") do
          group = model.active_entities.add_group
          group.name = name unless name.empty?
          entities = group.entities

          p1 = [x.mm, y.mm, z.mm]
          p2 = [(x + width).mm, y.mm, z.mm]
          p3 = [(x + width).mm, (y + depth).mm, z.mm]
          p4 = [x.mm, (y + depth).mm, z.mm]

          face = entities.add_face(p1, p2, p3, p4)
          raise "Không thể tạo mặt đáy" unless face
          face.reverse! if face.normal.z < 0
          face.pushpull(height.mm)

          Services::MetadataService.apply_material_to_group(group, model, material_name)
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "create_box",
          entity: Services::MetadataService.entity_metadata(group),
          dimensions_mm: { width: width, depth: depth, height: height },
          position_mm: [x, y, z],
          material: material_name.empty? ? nil : material_name,
          model_revision: Operation.model_revision
        }
      end

      def create_cylinder(args)
        radius = Float(args.fetch("radius"))
        height = Float(args.fetch("height"))

        Services::EntityService.validate_dimension!(radius, "radius")
        Services::EntityService.validate_dimension!(height, "height")

        segments = Integer(args["segments"] || 24)
        raise ArgumentError, "segments phải trong khoảng 3..256" unless segments.between?(3, 256)

        x = Float(args["x"] || 0.0)
        y = Float(args["y"] || 0.0)
        z = Float(args["z"] || 0.0)
        name = args["name"].to_s
        material_name = args["material"].to_s

        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        group = nil
        Operation.with_operation(model, "AI - Create Cylinder") do
          group = model.active_entities.add_group
          group.name = name unless name.empty?
          entities = group.entities

          circle = entities.add_circle([x.mm, y.mm, z.mm], [0, 0, 1], radius.mm, segments)
          face = entities.add_face(circle)
          raise "Không thể tạo mặt đáy hình trụ" unless face
          face.reverse! if face.normal.z < 0
          face.pushpull(height.mm)

          Services::MetadataService.apply_material_to_group(group, model, material_name)
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "create_cylinder",
          entity: Services::MetadataService.entity_metadata(group),
          radius_mm: radius,
          height_mm: height,
          segments: segments,
          position_mm: [x, y, z],
          material: material_name.empty? ? nil : material_name,
          model_revision: Operation.model_revision
        }
      end

      def create_wall(args)
        start_x = Float(args.fetch("start_x"))
        start_y = Float(args.fetch("start_y"))
        end_x = Float(args.fetch("end_x"))
        end_y = Float(args.fetch("end_y"))
        thickness = Float(args["thickness"] || 100.0)
        height = Float(args["height"] || 2800.0)
        z = Float(args["z"] || 0.0)
        name = args["name"].to_s.empty? ? "Wall" : args["name"].to_s
        material_name = args["material"].to_s

        Services::EntityService.validate_dimension!(thickness, "thickness")
        Services::EntityService.validate_dimension!(height, "height")

        dx = end_x - start_x
        dy = end_y - start_y
        length = Math.hypot(dx, dy)
        raise ArgumentError, "Chiều dài tường phải lớn hơn 0" if length <= 0
        Services::EntityService.validate_dimension!(length, "length")

        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        group = nil
        Operation.with_operation(model, "AI - Create Wall") do
          group = model.active_entities.add_group
          group.name = name
          entities = group.entities

          nx = (-dy / length) * (thickness / 2.0)
          ny = (dx / length) * (thickness / 2.0)

          p1 = [(start_x - nx).mm, (start_y - ny).mm, z.mm]
          p2 = [(end_x - nx).mm, (end_y - ny).mm, z.mm]
          p3 = [(end_x + nx).mm, (end_y + ny).mm, z.mm]
          p4 = [(start_x + nx).mm, (start_y + ny).mm, z.mm]

          face = entities.add_face(p1, p2, p3, p4)
          raise "Không thể tạo mặt tường" unless face
          face.reverse! if face.normal.z < 0
          face.pushpull(height.mm)

          Services::MetadataService.apply_material_to_group(group, model, material_name)
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "create_wall",
          entity: Services::MetadataService.entity_metadata(group),
          length_mm: length.round(1),
          thickness_mm: thickness,
          height_mm: height,
          material: material_name.empty? ? nil : material_name,
          model_revision: Operation.model_revision
        }
      end
    end
  end

  # Module-level delegates for backward compatibility
  def self.create_box(args)
    Handlers::Geometry.create_box(args)
  end

  def self.create_cylinder(args)
    Handlers::Geometry.create_cylinder(args)
  end

  def self.create_wall(args)
    Handlers::Geometry.create_wall(args)
  end
end
