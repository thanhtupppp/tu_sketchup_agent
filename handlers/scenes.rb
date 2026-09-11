# frozen_string_literal: true

module TuSketchupAgent
  module Handlers
    module Scenes
      extend self

      def register
        Router.register("get_layers") { |args| get_layers(args) }
        Router.register("create_layer") { |args| create_layer(args) }
        Router.register("set_entity_layer") { |args| set_entity_layer(args) }
        Router.register("set_layer_visibility") { |args| set_layer_visibility(args) }
        Router.register("get_scenes") { |args| get_scenes(args) }
        Router.register("create_scene") { |args| create_scene(args) }
        Router.register("activate_scene") { |args| activate_scene(args) }
        Router.register("set_camera_view") { |args| set_camera_view(args) }
      end

      def get_layers(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        name_filter = args["name_filter"].to_s.downcase.strip
        items = []
        model.layers.each do |layer|
          next if !name_filter.empty? && !layer.name.downcase.include?(name_filter)
          items << Services::MetadataService.layer_metadata(layer)
        end

        {
          ok: true,
          total_count: items.length,
          layers: items,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def create_layer(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        name = (args["name"] || args["layer_name"]).to_s.strip
        raise ArgumentError, "Tên layer không được để trống" if name.empty?

        layer = nil
        created_new = false
        Operation.with_operation(model, "AI - Create Layer") do
          existing = model.layers[name]
          if existing
            layer = existing
          else
            layer = model.layers.add(name)
            created_new = true
          end

          if args["color"]
            c_val = args["color"]
            if c_val.is_a?(Array) && c_val.length >= 3
              layer.color = Sketchup::Color.new(c_val[0], c_val[1], c_val[2])
            elsif c_val.is_a?(String) && !c_val.empty?
              layer.color = Sketchup::Color.new(c_val)
            end
          end

          if args.key?("visible")
            layer.visible = !!args["visible"]
          end

          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "create_layer",
          created_new: created_new,
          layer: Services::MetadataService.layer_metadata(layer),
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def set_entity_layer(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        layer_name = (args["layer_name"] || args["name"]).to_s.strip
        raise ArgumentError, "Tên layer không được để trống" if layer_name.empty?

        entities, missing_ids = Services::EntityService.resolve_entities_from_args(model, args)
        raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ" if entities.empty?

        # Type safety guard: chỉ cho phép Group hoặc ComponentInstance
        entities.each do |e|
          Services::EntityService.validate_group_or_component!(e)
        end

        layer = nil
        Operation.with_operation(model, "AI - Set Entity Layer") do
          layer = model.layers[layer_name] || model.layers.add(layer_name)
          entities.each do |e|
            e.layer = layer
          end
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "set_entity_layer",
          updated_count: entities.length,
          layer_name: layer.name,
          entities: entities.map { |e| Services::MetadataService.entity_metadata(e) },
          missing_ids: missing_ids,
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def set_layer_visibility(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        updated = {}
        Operation.with_operation(model, "AI - Set Layer Visibility") do
          if args["layers"].is_a?(Hash)
            args["layers"].each do |lname, vis|
              lay = model.layers[lname.to_s]
              if lay
                lay.visible = !!vis
                updated[lay.name] = lay.visible?
              end
            end
          elsif args["layer_name"] || args["name"]
            lname = (args["layer_name"] || args["name"]).to_s.strip
            lay = model.layers[lname]
            raise ArgumentError, "Không tìm thấy layer '#{lname}'" unless lay
            vis = args.key?("visible") ? !!args["visible"] : true
            lay.visible = vis
            updated[lay.name] = lay.visible?
          else
            raise ArgumentError, "Cần cung cấp layer_name hoặc dictionary layers"
          end
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "set_layer_visibility",
          updated_layers: updated,
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def get_scenes(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        name_filter = args["name_filter"].to_s.downcase.strip
        items = []
        model.pages.each do |page|
          next if !name_filter.empty? && !page.name.downcase.include?(name_filter)
          cam = page.camera
          hidden = []
          model.layers.each do |lay|
            hidden << lay.name unless page.layer_visible?(lay) rescue nil
          end
          items << {
            name: page.name,
            page_id: page.entityID,
            camera: Services::MetadataService.camera_metadata(cam),
            hidden_layers: hidden,
            transition_time: page.transition_time
          }
        end

        selected_name = model.pages.selected_page ? model.pages.selected_page.name : nil

        {
          ok: true,
          total_count: items.length,
          current_scene: selected_name,
          scenes: items,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def create_scene(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        name = (args["name"] || args["scene_name"]).to_s.strip
        raise ArgumentError, "Tên scene không được để trống" if name.empty?

        page = nil
        Operation.with_operation(model, "AI - Create Scene") do
          existing = model.pages[name]
          page = existing || model.pages.add(name)

          if args["preset"]
            Services::TransformationService.setup_camera_preset(page.camera, args["preset"], args["perspective"] == true)
          elsif args["camera"].is_a?(Hash)
            cam_data = args["camera"]
            if cam_data["eye"].is_a?(Array) && cam_data["target"].is_a?(Array)
              eye_pt = Geom::Point3d.new(cam_data["eye"].map { |v| Float(v).mm })
              tgt_pt = Geom::Point3d.new(cam_data["target"].map { |v| Float(v).mm })
              up_vec = if cam_data["up"].is_a?(Array)
                Geom::Vector3d.new(cam_data["up"].map { |v| Float(v) })
              else
                Geom::Vector3d.new(0, 0, 1)
              end
              page.camera.perspective = cam_data["perspective"] == true
              page.camera.set(eye_pt, tgt_pt, up_vec)
            end
          end

          if args["hidden_layers"].is_a?(Array)
            args["hidden_layers"].each do |lname|
              lay = model.layers[lname.to_s]
              page.set_visibility(lay, false) if lay
            end
          end

          page.update(PAGE_USE_ALL)
          Operation.bump_model_revision
        end

        {
          ok: true,
          operation: "create_scene",
          scene: {
            name: page.name,
            page_id: page.entityID,
            camera: Services::MetadataService.camera_metadata(page.camera)
          },
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def activate_scene(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        name = (args["name"] || args["scene_name"]).to_s.strip
        raise ArgumentError, "Thiếu tham số tên scene" if name.empty?

        page = model.pages[name]
        raise ArgumentError, "Không tìm thấy scene '#{name}' trong model" unless page

        model.pages.selected_page = page

        {
          ok: true,
          operation: "activate_scene",
          scene_name: page.name,
          page_id: page.entityID,
          camera: Services::MetadataService.camera_metadata(model.active_view.camera),
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end

      def set_camera_view(args)
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        view = model.active_view
        camera = view.camera

        if args["preset"]
          Services::TransformationService.setup_camera_preset(camera, args["preset"], args["perspective"] == true)
        elsif args["eye"].is_a?(Array) && args["target"].is_a?(Array)
          eye_pt = Geom::Point3d.new(args["eye"].map { |v| Float(v).mm })
          tgt_pt = Geom::Point3d.new(args["target"].map { |v| Float(v).mm })
          up_vec = if args["up"].is_a?(Array)
            Geom::Vector3d.new(args["up"].map { |v| Float(v) })
          else
            Geom::Vector3d.new(0, 0, 1)
          end
          camera.perspective = args["perspective"] == true
          camera.set(eye_pt, tgt_pt, up_vec)
        end

        if args["zoom_extents"] == true
          view.zoom_extents
        end

        view.invalidate

        {
          ok: true,
          operation: "set_camera_view",
          camera: Services::MetadataService.camera_metadata(camera),
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION
        }
      end
    end
  end

  # Module-level delegates for backward compatibility
  def self.get_layers(args)
    Handlers::Scenes.get_layers(args)
  end

  def self.create_layer(args)
    Handlers::Scenes.create_layer(args)
  end

  def self.set_entity_layer(args)
    Handlers::Scenes.set_entity_layer(args)
  end

  def self.set_layer_visibility(args)
    Handlers::Scenes.set_layer_visibility(args)
  end

  def self.get_scenes(args)
    Handlers::Scenes.get_scenes(args)
  end

  def self.create_scene(args)
    Handlers::Scenes.create_scene(args)
  end

  def self.activate_scene(args)
    Handlers::Scenes.activate_scene(args)
  end

  def self.set_camera_view(args)
    Handlers::Scenes.set_camera_view(args)
  end
end
