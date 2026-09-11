# frozen_string_literal: true

module TuSketchupAgent
  module Handlers
    module Components
      extend self

      def register
        Router.register("create_component") { |args| create_component(args) }
        Router.register("get_component_definitions") { |args| get_component_definitions(args) }
        Router.register("make_component_unique") { |args| make_component_unique(args) }
        Router.register("save_component_to_skp") { |args| save_component_to_skp(args) }
        Router.register("load_component_from_skp") { |args| load_component_from_skp(args) }
      end

      def create_component(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        name = (args["name"] || args["component_name"]).to_s.strip
        raise ArgumentError, "Tên component không được để trống" if name.empty?

        entities, missing_ids = Services::EntityService.resolve_entities_from_args(model, args)
        raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để tạo component" if entities.empty?

        description = args["description"].to_s

        instance = nil
        definition = nil

        Operation.with_operation(model, "AI - Create Component") do
          if entities.length == 1 && entities.first.is_a?(Sketchup::Group)
            instance = entities.first.to_component
          else
            temp_group = model.active_entities.add_group(entities)
            instance = temp_group.to_component
          end
          definition = instance.definition
          definition.name = name
          definition.description = description unless description.empty?
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "create_component",
          definition: {
            name: definition.name,
            guid: definition.guid,
            instances_count: definition.instances.length,
            description: definition.description
          },
          instance: Services::MetadataService.entity_metadata(instance),
          missing_ids: missing_ids,
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def get_component_definitions(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        include_internal = args["include_internal"] == true
        name_filter = args["name_filter"].to_s.downcase.strip

        items = []
        model.definitions.each do |defn|
          next if !include_internal && defn.group?
          next if !name_filter.empty? && !defn.name.downcase.include?(name_filter)

          bbox = defn.bounds
          items << {
            name: defn.name,
            guid: defn.guid,
            instances_count: defn.instances.length,
            description: defn.description,
            is_group_internal: defn.group?,
            bounds_mm: bbox ? {
              width: bbox.width.to_mm.round(1),
              depth: bbox.height.to_mm.round(1),
              height: bbox.depth.to_mm.round(1)
            } : nil
          }
        end

        {
          ok: true,
          total_count: items.length,
          definitions: items,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def make_component_unique(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        entities, missing_ids = Services::EntityService.resolve_entities_from_args(model, args)
        raise ArgumentError, "Không tìm thấy instance nào để make_unique" if entities.empty?

        components = entities.select { |e| e.is_a?(Sketchup::ComponentInstance) }
        raise ArgumentError, "Không có ComponentInstance nào trong danh sách được cung cấp" if components.empty?

        new_name = args["new_name"].to_s.strip

        Operation.with_operation(model, "AI - Make Component Unique") do
          components.each do |comp|
            comp.make_unique
            comp.definition.name = new_name if !new_name.empty? && components.length == 1
          end
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "make_component_unique",
          updated_count: components.length,
          new_definition_name: components.first.definition.name,
          missing_ids: missing_ids,
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def save_component_to_skp(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        name = (args["definition_name"] || args["name"]).to_s.strip
        raise ArgumentError, "Thiếu tham số definition_name" if name.empty?

        defn = model.definitions[name]
        raise ArgumentError, "Không tìm thấy definition '#{name}' trong model" unless defn

        file_path = args["file_path"].to_s.strip
        raise ArgumentError, "Thiếu tham số file_path" if file_path.empty?
        raise ArgumentError, "Đường dẫn file phải có đuôi .skp" unless file_path.downcase.end_with?(".skp")

        dir = File.dirname(file_path)
        raise ArgumentError, "Thư mục không tồn tại: #{dir}" unless Dir.exist?(dir)

        overwrite = args["overwrite"] == true
        if File.exist?(file_path) && !overwrite
          raise ArgumentError, "File '#{file_path}' đã tồn tại (dùng overwrite: true nếu muốn ghi đè)"
        end

        success = defn.save_as(file_path)
        raise "Lỗi lưu definition ra file .skp" unless success

        {
          ok: true,
          operation: "save_component_to_skp",
          definition_name: defn.name,
          file_path: file_path,
          file_size_bytes: File.size(file_path),
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def load_component_from_skp(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        file_path = args["file_path"].to_s.strip
        raise ArgumentError, "Thiếu tham số file_path" if file_path.empty?
        raise ArgumentError, "File không tồn tại: #{file_path}" unless File.exist?(file_path)
        raise ArgumentError, "File phải có định dạng .skp" unless file_path.downcase.end_with?(".skp")

        defn = nil
        Operation.with_operation(model, "AI - Load Component From SKP") do
          defn = model.definitions.load(file_path)
          if args["definition_name"] && !args["definition_name"].to_s.strip.empty?
            defn.name = args["definition_name"].to_s.strip
          end
          Operation.bump_model_revision
        end

        bbox = defn.bounds
        {
          ok: true,
          operation: "load_component_from_skp",
          definition: {
            name: defn.name,
            guid: defn.guid,
            instances_count: defn.instances.length,
            bounds_mm: bbox ? {
              width: bbox.width.to_mm.round(1),
              depth: bbox.height.to_mm.round(1),
              height: bbox.depth.to_mm.round(1)
            } : nil
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
  def self.create_component(args)
    Handlers::Components.create_component(args)
  end

  def self.get_component_definitions(args)
    Handlers::Components.get_component_definitions(args)
  end

  def self.make_component_unique(args)
    Handlers::Components.make_component_unique(args)
  end

  def self.save_component_to_skp(args)
    Handlers::Components.save_component_to_skp(args)
  end

  def self.load_component_from_skp(args)
    Handlers::Components.load_component_from_skp(args)
  end
end
