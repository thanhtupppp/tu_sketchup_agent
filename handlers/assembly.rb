# frozen_string_literal: true

module TuSketchupAgent
  module Handlers
    module Assembly
      extend self

      def register
        Router.register("place_component_instance") { |args| place_component_instance(args) }
        Router.register("import_file") { |args| import_file(args) }
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

      def import_file(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        file_path = args["file_path"].to_s.strip
        raise ArgumentError, "Thiếu tham số file_path" if file_path.empty?

        file_path = File.expand_path(file_path, TuSketchupAgent::PLUGIN_DIR) unless File.exist?(file_path)
        raise ArgumentError, "Không tìm thấy tệp: #{file_path}" unless File.exist?(file_path)

        ext = File.extname(file_path).downcase
        supported_exts = [".dwg", ".dxf", ".dae", ".3ds", ".obj", ".ifc", ".skp", ".dem", ".ddf"]
        raise ArgumentError, "Định dạng tệp '#{ext}' không được hỗ trợ. Các định dạng hỗ trợ: #{supported_exts.join(', ')}" unless supported_exts.include?(ext)

        units = (args["units"] || "mm").to_s.downcase
        merge_coplanar = args.key?("merge_coplanar_faces") ? !!args["merge_coplanar_faces"] : true
        orient_faces = args.key?("orient_faces") ? !!args["orient_faces"] : true
        preserve_origin = args.key?("preserve_origin") ? !!args["preserve_origin"] : true
        as_component = args.key?("as_component") ? !!args["as_component"] : true
        custom_name = args["name"].to_s.strip

        unit_option = case units
        when "mm", "millimeter", "millimeters" then "mm"
        when "cm", "centimeter", "centimeters" then "cm"
        when "m", "meter", "meters" then "m"
        when "in", "inch", "inches" then "in"
        when "ft", "feet", "foot" then "ft"
        else "mm"
        end

        options = {
          units: unit_option,
          merge_coplanar_faces: merge_coplanar,
          orient_faces: orient_faces,
          preserve_origin: preserve_origin,
          show_summary: false
        }

        existing_layers = model.layers.map(&:name)
        before_entities_count = model.active_entities.length

        imported_entity = nil
        imported_defn = nil

        Operation.with_operation(model, "AI - Import File: #{File.basename(file_path)}") do
          if ext == ".skp"
            imported_defn = model.definitions.load(file_path)
            imported_defn.name = custom_name unless custom_name.empty?
            if as_component
              imported_entity = model.active_entities.add_instance(imported_defn, Geom::Transformation.new)
            end
          else
            defn_imported = false
            if as_component && model.definitions.respond_to?(:import)
              begin
                imported_defn = model.definitions.import(file_path, options)
                if imported_defn
                  imported_defn.name = custom_name unless custom_name.empty?
                  imported_entity = model.active_entities.add_instance(imported_defn, Geom::Transformation.new)
                  defn_imported = true
                end
              rescue StandardError => err
                puts "TuSketchupAgent: DefinitionList.import fallback to model.import: #{err.message}"
              end
            end

            unless defn_imported
              success = model.import(file_path, false)
              raise "Lỗi khi nạp tệp qua SketchUp Importer: #{file_path}" unless success

              new_entities = model.active_entities.to_a[before_entities_count..-1] || []
              if new_entities.length == 1 && (new_entities.first.is_a?(Sketchup::Group) || new_entities.first.is_a?(Sketchup::ComponentInstance))
                imported_entity = new_entities.first
                imported_entity.name = custom_name unless custom_name.empty?
              elsif new_entities.length > 1 && as_component
                grp = model.active_entities.add_group(new_entities)
                grp.name = custom_name.empty? ? File.basename(file_path, ".*") : custom_name
                imported_entity = grp
              end
            end
          end

          Operation.bump_model_revision
        end

        new_layers = model.layers.map(&:name) - existing_layers

        bbox_data = nil
        pid = nil
        ent_type = nil

        if imported_entity
          pid = imported_entity.persistent_id rescue imported_entity.entityID
          ent_type = imported_entity.class.name.split("::").last
          bbox = imported_entity.bounds
          bbox_data = {
            width: bbox.width.to_mm.round(1),
            depth: bbox.height.to_mm.round(1),
            height: bbox.depth.to_mm.round(1),
            min: [bbox.min.x.to_mm.round(1), bbox.min.y.to_mm.round(1), bbox.min.z.to_mm.round(1)],
            max: [bbox.max.x.to_mm.round(1), bbox.max.y.to_mm.round(1), bbox.max.z.to_mm.round(1)],
            center: [bbox.center.x.to_mm.round(1), bbox.center.y.to_mm.round(1), bbox.center.z.to_mm.round(1)]
          }
        elsif imported_defn
          bbox = imported_defn.bounds
          bbox_data = {
            width: bbox.width.to_mm.round(1),
            depth: bbox.height.to_mm.round(1),
            height: bbox.depth.to_mm.round(1)
          }
        end

        {
          ok: true,
          operation: "import_file",
          file_path: file_path,
          file_name: File.basename(file_path),
          file_extension: ext,
          units: units,
          definition_name: imported_defn ? imported_defn.name : nil,
          persistent_id: pid,
          entity_type: ent_type,
          bounds: bbox_data,
          new_layers: new_layers,
          total_layers_count: model.layers.length,
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end
    end
  end

  # Module-level delegates for backward compatibility
  def place_component_instance(args)
    Handlers::Assembly.place_component_instance(args)
  end

  def import_file(args)
    Handlers::Assembly.import_file(args)
  end
end
