# frozen_string_literal: true

module TuSketchupAgent
  module Handlers
    module Materials
      extend self

      def register
        Router.register("get_materials") { |args| get_materials(args) }
        Router.register("get_material_info") { |args| get_material_info(args) }
        Router.register("create_material") { |args| create_material(args) }
        Router.register("set_entity_material") { |args| set_entity_material(args) }
        Router.register("clear_entity_material") { |args| clear_entity_material(args) }
      end

      def get_materials(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        limit = (args["limit"] || 100).to_i.clamp(1, 1000)
        offset = (args["offset"] || 0).to_i
        offset = 0 if offset < 0
        name_filter = args["name_filter"].to_s.strip.downcase

        all_mats = model.materials.to_a
        if !name_filter.empty?
          all_mats.select! { |m| m.name.downcase.include?(name_filter) }
        end

        total_count = all_mats.length
        sliced = all_mats.slice(offset, limit) || []
        items = sliced.map { |m| Services::MetadataService.material_metadata(m) }

        {
          ok: true,
          total_count: total_count,
          returned_count: items.length,
          offset: offset,
          limit: limit,
          materials: items,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def get_material_info(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        name = (args["name"] || args["material_name"]).to_s.strip
        raise ArgumentError, "Thiếu tham số tên vật liệu (name hoặc material_name)" if name.empty?

        mat = model.materials[name]
        raise ArgumentError, "Không tìm thấy vật liệu có tên '#{name}' trong model" unless mat

        {
          ok: true,
          material: Services::MetadataService.material_metadata(mat),
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def create_material(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        name = (args["name"] || args["material_name"]).to_s.strip
        raise ArgumentError, "Tên vật liệu không được để trống" if name.empty?

        mat = model.materials[name]
        created_new = mat.nil?

        Operation.with_operation(model, "AI - Create/Update Material") do
          mat ||= model.materials.add(name)

          # Handle color
          if args["color"]
            c_arg = args["color"]
            if c_arg.is_a?(Array) && c_arg.length >= 3
              mat.color = Sketchup::Color.new(c_arg[0].to_i, c_arg[1].to_i, c_arg[2].to_i, (c_arg[3] || 255).to_i)
            elsif c_arg.is_a?(String) && !c_arg.strip.empty?
              mat.color = Sketchup::Color.new(c_arg.strip)
            end
          end

          # Handle alpha
          if args.key?("alpha")
            alpha_val = Float(args["alpha"]).clamp(0.0, 1.0)
            mat.alpha = alpha_val
          end

          # Handle texture
          if args["texture_path"] && !args["texture_path"].to_s.strip.empty?
            tex_path = args["texture_path"].to_s.strip
            if File.exist?(tex_path)
              mat.texture = tex_path
              tex = mat.texture
              if tex
                tex.width = Float(args["texture_width"]).mm if args["texture_width"]
                tex.height = Float(args["texture_height"]).mm if args["texture_height"]
              end
            else
              raise ArgumentError, "File texture không tồn tại: #{tex_path}"
            end
          end

          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "create_material",
          created_new: created_new,
          material: Services::MetadataService.material_metadata(mat),
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def set_entity_material(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        mat_name = (args["material_name"] || args["name"]).to_s.strip
        raise ArgumentError, "Thiếu tham số tên vật liệu (material_name)" if mat_name.empty?

        mat = model.materials[mat_name]
        raise ArgumentError, "Vật liệu '#{mat_name}' chưa tồn tại trong model" unless mat

        entities, missing_ids = Services::EntityService.resolve_entities_from_args(model, args)
        raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để gán vật liệu" if entities.empty?

        entities.each do |e|
          Services::EntityService.validate_group_or_component!(e)
        end

        Operation.with_operation(model, "AI - Set Entity Material") do
          entities.each do |e|
            e.material = mat
          end
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "set_entity_material",
          updated_count: entities.length,
          material_name: mat_name,
          missing_ids: missing_ids,
          entities: entities.map { |e| Services::MetadataService.entity_metadata(e) },
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def clear_entity_material(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        entities, missing_ids = Services::EntityService.resolve_entities_from_args(model, args)
        raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để xóa vật liệu" if entities.empty?

        entities.each do |e|
          Services::EntityService.validate_group_or_component!(e)
        end

        Operation.with_operation(model, "AI - Clear Entity Material") do
          entities.each do |e|
            e.material = nil
          end
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "clear_entity_material",
          cleared_count: entities.length,
          missing_ids: missing_ids,
          entities: entities.map { |e| Services::MetadataService.entity_metadata(e) },
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end
    end
  end

  # Module-level delegates for backward compatibility
  def self.get_materials(args)
    Handlers::Materials.get_materials(args)
  end

  def self.get_material_info(args)
    Handlers::Materials.get_material_info(args)
  end

  def self.create_material(args)
    Handlers::Materials.create_material(args)
  end

  def self.set_entity_material(args)
    Handlers::Materials.set_entity_material(args)
  end

  def self.clear_entity_material(args)
    Handlers::Materials.clear_entity_material(args)
  end
end
