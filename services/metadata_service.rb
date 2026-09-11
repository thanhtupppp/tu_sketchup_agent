# frozen_string_literal: true

module TuSketchupAgent
  module Services
    module MetadataService
      extend self

      def apply_material_to_group(group, model, material_name)
        return if material_name.to_s.empty?

        material = model.materials[material_name] || model.materials.add(material_name)
        group.material = material
        group.entities.grep(Sketchup::Face).each do |face|
          face.material = material
          face.back_material = material
        end
      end

      def camera_metadata(camera)
        return nil unless camera
        eye = camera.eye
        target = camera.target
        up = camera.up
        {
          eye_mm: [eye.x.to_mm.round(1), eye.y.to_mm.round(1), eye.z.to_mm.round(1)],
          target_mm: [target.x.to_mm.round(1), target.y.to_mm.round(1), target.z.to_mm.round(1)],
          up: [up.x.round(3), up.y.round(3), up.z.round(3)],
          perspective: camera.perspective?,
          fov: camera.fov.round(1)
        }
      end

      def layer_metadata(layer)
        return nil unless layer
        c = layer.color rescue nil
        {
          name: layer.name,
          visible: layer.visible?,
          color_hex: c ? sprintf("#%02X%02X%02X", c.red, c.green, c.blue) : nil,
          color_rgb: c ? [c.red, c.green, c.blue] : nil
        }
      end

      def material_metadata(mat)
        return nil unless mat && mat.valid?
        c = mat.color
        tex = mat.texture
        {
          name: mat.name,
          display_name: mat.display_name,
          color_rgb: [c.red, c.green, c.blue, c.alpha],
          color_hex: sprintf("#%02X%02X%02X", c.red, c.green, c.blue),
          alpha: mat.alpha.round(3),
          has_texture: !tex.nil?,
          texture: tex ? {
            filename: tex.filename,
            width_mm: tex.width.to_mm.round(1),
            height_mm: tex.height.to_mm.round(1)
          } : nil
        }
      end

      def entity_metadata(entity)
        return nil unless entity
        pid = entity.respond_to?(:persistent_id) ? entity.persistent_id : nil
        eid = entity.respond_to?(:entityID) ? entity.entityID : nil
        {
          entity_id: eid,
          persistent_id: pid,
          type: entity.class.name.sub("Sketchup::", ""),
          name: entity.respond_to?(:name) ? entity.name : nil,
          layer: entity.respond_to?(:layer) && entity.layer ? entity.layer.name : "Layer0"
        }
      end
    end
  end

  # Module-level delegates for backward compatibility
  def self.apply_material_to_group(group, model, material_name)
    Services::MetadataService.apply_material_to_group(group, model, material_name)
  end

  def self.camera_metadata(camera)
    Services::MetadataService.camera_metadata(camera)
  end

  def self.layer_metadata(layer)
    Services::MetadataService.layer_metadata(layer)
  end

  def self.material_metadata(mat)
    Services::MetadataService.material_metadata(mat)
  end

  def self.entity_metadata(entity)
    Services::MetadataService.entity_metadata(entity)
  end
end
