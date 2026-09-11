# frozen_string_literal: true

module TuSketchupAgent
  module Services
    module TransformationService
      extend self

      def build_transformation(args)
        # 1. Chế độ Raw Matrix 4x4 (16 số thực)
        if args["matrix"].is_a?(Array) && args["matrix"].length == 16
          raw_vals = args["matrix"].map { |v| Float(v) }
          return Geom::Transformation.new(raw_vals)
        end

        # 2. Chế độ tham số trực quan: Scale * Rotation * Translation
        # Scale
        t_scale = if args["scale"].is_a?(Array) && args["scale"].length == 3
          Geom::Transformation.scaling(Float(args["scale"][0]), Float(args["scale"][1]), Float(args["scale"][2]))
        elsif args["scale"] && Float(args["scale"]) != 1.0
          s = Float(args["scale"])
          Geom::Transformation.scaling(s, s, s)
        else
          Geom::Transformation.new
        end

        # Rotation
        t_rot = Geom::Transformation.new
        if args["rotation"].is_a?(Hash)
          axis_str = (args["rotation"]["axis"] || "z").to_s.downcase
          axis_vec = case axis_str
          when "x" then Geom::Vector3d.new(1, 0, 0)
          when "y" then Geom::Vector3d.new(0, 1, 0)
          else Geom::Vector3d.new(0, 0, 1)
          end
          angle_deg = Float(args["rotation"]["angle"] || 0.0)
          t_rot = Geom::Transformation.rotation(Geom::Point3d.new(0, 0, 0), axis_vec, angle_deg.degrees) if angle_deg != 0.0
        elsif args["rotation"].is_a?(Array) && args["rotation"].length == 3
          rx, ry, rz = args["rotation"].map { |v| Float(v) }
          tr_x = rx != 0 ? Geom::Transformation.rotation(Geom::Point3d.new(0, 0, 0), Geom::Vector3d.new(1, 0, 0), rx.degrees) : Geom::Transformation.new
          tr_y = ry != 0 ? Geom::Transformation.rotation(Geom::Point3d.new(0, 0, 0), Geom::Vector3d.new(0, 1, 0), ry.degrees) : Geom::Transformation.new
          tr_z = rz != 0 ? Geom::Transformation.rotation(Geom::Point3d.new(0, 0, 0), Geom::Vector3d.new(0, 0, 1), rz.degrees) : Geom::Transformation.new
          t_rot = tr_z * tr_y * tr_x
        end

        # Translation (Position in mm)
        t_pos = Geom::Transformation.new
        if args["position"].is_a?(Array) && args["position"].length >= 3
          px = Float(args["position"][0]).mm
          py = Float(args["position"][1]).mm
          pz = Float(args["position"][2]).mm
          t_pos = Geom::Transformation.translation(Geom::Point3d.new(px, py, pz))
        end

        t_pos * t_rot * t_scale
      end

      def setup_camera_preset(camera, preset, perspective = false, bounds = nil)
        bounds ||= Sketchup.active_model.bounds
        cx = bounds.center.x
        cy = bounds.center.y
        cz = bounds.center.z
        diag = bounds.diagonal
        diag = 1000.mm if diag.nil? || diag < 1.mm
        dist = diag * 2.0

        camera.perspective = !!perspective

        case preset.to_s.downcase.strip
        when "top"
          eye = Geom::Point3d.new(cx, cy, cz + dist)
          target = Geom::Point3d.new(cx, cy, cz)
          up = Geom::Vector3d.new(0, 1, 0)
        when "front"
          eye = Geom::Point3d.new(cx, cy - dist, cz)
          target = Geom::Point3d.new(cx, cy, cz)
          up = Geom::Vector3d.new(0, 0, 1)
        when "right"
          eye = Geom::Point3d.new(cx + dist, cy, cz)
          target = Geom::Point3d.new(cx, cy, cz)
          up = Geom::Vector3d.new(0, 0, 1)
        when "left"
          eye = Geom::Point3d.new(cx - dist, cy, cz)
          target = Geom::Point3d.new(cx, cy, cz)
          up = Geom::Vector3d.new(0, 0, 1)
        when "back"
          eye = Geom::Point3d.new(cx, cy + dist, cz)
          target = Geom::Point3d.new(cx, cy, cz)
          up = Geom::Vector3d.new(0, 0, 1)
        when "iso"
          offset = dist / Math.sqrt(3)
          eye = Geom::Point3d.new(cx + offset, cy - offset, cz + offset)
          target = Geom::Point3d.new(cx, cy, cz)
          up = Geom::Vector3d.new(0, 0, 1)
        else
          return camera
        end

        camera.set(eye, target, up)
        camera
      end

      def calculate_bounds_mm(entities)
        bb = Geom::BoundingBox.new
        entities.each do |e|
          bb.add(e.bounds) if e && e.respond_to?(:bounds) && e.valid?
        end
        return nil if bb.empty?
        {
          width: bb.width.to_mm.round(1),
          depth: bb.height.to_mm.round(1),
          height: bb.depth.to_mm.round(1),
          center: [bb.center.x.to_mm.round(1), bb.center.y.to_mm.round(1), bb.center.z.to_mm.round(1)],
          min: [bb.min.x.to_mm.round(1), bb.min.y.to_mm.round(1), bb.min.z.to_mm.round(1)],
          max: [bb.max.x.to_mm.round(1), bb.max.y.to_mm.round(1), bb.max.z.to_mm.round(1)]
        }
      end
    end
  end

  # Module-level delegates for backward compatibility
  def self.build_transformation(args)
    Services::TransformationService.build_transformation(args)
  end

  def self.setup_camera_preset(camera, preset, perspective = false, bounds = nil)
    Services::TransformationService.setup_camera_preset(camera, preset, perspective, bounds)
  end

  def self.calculate_bounds_mm(entities)
    Services::TransformationService.calculate_bounds_mm(entities)
  end
end
