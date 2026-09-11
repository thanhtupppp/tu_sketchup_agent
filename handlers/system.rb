# frozen_string_literal: true

require "base64"
require "tmpdir"

module TuSketchupAgent
  module Handlers
    module System
      extend self

      def register
        Router.register("ping") { ping_response }
        Router.register("model_summary") { model_summary }
        Router.register("get_selection") { get_selection }
        Router.register("zoom_extents") { zoom_extents }
        Router.register("capture_viewport") { |args| capture_viewport(args) }
        Router.register("execute_ruby") { |args| execute_ruby(args) }
      end

      def ping_response
        {
          ok: true,
          service: "tu-sketchup-agent",
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION,
          sketchup_version: Sketchup.version,
          server: "#{TuSketchupAgent::HOST}:#{TuSketchupAgent::PORT}",
          dev_mode: Auth.dev_mode?
        }
      end

      def model_summary
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        bbox = model.bounds
        {
          ok: true,
          service: "tu-sketchup-agent",
          protocol_version: TuSketchupAgent::PROTOCOL_VERSION,
          min_compatible_protocol_version: TuSketchupAgent::MIN_COMPATIBLE_PROTOCOL_VERSION,
          sketchup_version: Sketchup.version,
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision,
          model_revision_source: "tu-sketchup-agent",
          capabilities: {
            find_entity_by_persistent_id: model.respond_to?(:find_entity_by_persistent_id),
            find_entity_by_id: model.respond_to?(:find_entity_by_id)
          },
          title: model.title.empty? ? "Untitled" : model.title,
          path: model.path,
          entity_count: model.active_entities.length,
          selection_count: model.selection.length,
          layers: model.layers.map(&:name),
          materials: model.materials.map(&:name),
          scenes: model.pages.map(&:name),
          bounds_mm: {
            width: bbox.width.to_mm.round(1),
            depth: bbox.height.to_mm.round(1),
            height: bbox.depth.to_mm.round(1)
          }
        }
      end

      def get_selection
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        items = model.selection.map do |entity|
          bbox = entity.respond_to?(:bounds) ? entity.bounds : nil
          meta = Services::MetadataService.entity_metadata(entity)
          meta.merge(
            material: entity.respond_to?(:material) && entity.material ? entity.material.name : nil,
            bounds_mm: bbox ? {
              width: bbox.width.to_mm.round(1),
              depth: bbox.height.to_mm.round(1),
              height: bbox.depth.to_mm.round(1),
              center: [bbox.center.x.to_mm.round(1), bbox.center.y.to_mm.round(1), bbox.center.z.to_mm.round(1)]
            } : nil
          )
        end

        { ok: true, count: items.length, items: items }
      end

      def zoom_extents
        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        model.active_view.zoom_extents
        { ok: true, operation: "zoom_extents" }
      end

      def capture_viewport(args)
        width = (args["width"] || 1280).to_i
        height = (args["height"] || 720).to_i
        raise ArgumentError, "width phải trong khoảng 64..4096" unless width.between?(64, 4096)
        raise ArgumentError, "height phải trong khoảng 64..4096" unless height.between?(64, 4096)

        output_path = args["output_path"].to_s.strip
        is_temp = output_path.empty?
        target_file = is_temp ? File.join(Dir.tmpdir, "sketchup_vp_#{Time.now.to_i}_#{rand(1000)}.png") : output_path

        include_base64 = args.fetch("include_base64", false)

        model = Sketchup.active_model
        raise "Không có model nào đang mở" unless model

        view = model.active_view

        view.write_image({
          filename: target_file,
          width: width,
          height: height,
          antialias: true,
          compression: 0.9
        })

        image_written = File.exist?(target_file)
        b64_data = (include_base64 && image_written) ? Base64.strict_encode64(File.binread(target_file)) : nil

        {
          ok: true,
          width: width,
          height: height,
          image_path: is_temp ? nil : target_file,
          image_available: image_written,
          image_base64: b64_data
        }
      ensure
        File.delete(target_file) if is_temp && target_file && File.exist?(target_file)
      end

      def execute_ruby(args)
        unless Auth.dev_mode?
          return {
            ok: false,
            error: {
              code: "DEV_MODE_REQUIRED",
              message: "execute_ruby bị vô hiệu hóa ngoài dev mode (bật TU_SKETCHUP_DEV_MODE=1 hoặc qua menu Extension)",
              class: "SecurityError"
            }
          }
        end

        code = args["code"].to_s
        if code.strip.empty?
          return {
            ok: false,
            error: {
              code: "INVALID_ARGUMENT",
              message: "Thiếu code ruby"
            }
          }
        end

        if code.bytesize > 100_000
          return {
            ok: false,
            error: {
              code: "PAYLOAD_TOO_LARGE",
              message: "Code vượt quá giới hạn 100 KB"
            }
          }
        end

        auto_op = args.fetch("auto_operation", false)
        model = Sketchup.active_model

        puts "TuSketchupAgent: [execute_ruby] #{code.slice(0, 80).strip}..."

        result = nil
        if auto_op && model
          Operation.with_operation(model, "AI Ruby Execution") do
            result = eval(code, TOPLEVEL_BINDING)
            Operation.bump_model_revision
          end
        else
          result = eval(code, TOPLEVEL_BINDING)
        end

        {
          ok: true,
          result: result.inspect,
          class: result.class.name,
          model_revision: Operation.model_revision,
          mcp_revision: Operation.model_revision
        }
      rescue StandardError => error
        err = {
          code: "RUBY_EXECUTION_ERROR",
          message: error.message,
          class: error.class.name
        }
        err[:backtrace] = error.backtrace.first(5) if Auth.dev_mode? && error.backtrace
        {
          ok: false,
          error: err
        }
      end
    end
  end

  # Module-level delegates for backward compatibility
  def self.ping_response
    Handlers::System.ping_response
  end

  def self.model_summary
    Handlers::System.model_summary
  end

  def self.get_selection
    Handlers::System.get_selection
  end

  def self.zoom_extents
    Handlers::System.zoom_extents
  end

  def self.capture_viewport(args)
    Handlers::System.capture_viewport(args)
  end

  def self.execute_ruby(args)
    Handlers::System.execute_ruby(args)
  end
end
