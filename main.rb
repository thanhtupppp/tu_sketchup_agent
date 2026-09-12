# frozen_string_literal: true

require "sketchup.rb"

module TuSketchupAgent
  extend self

  PLUGIN_DIR = File.dirname(__FILE__) unless const_defined?(:PLUGIN_DIR)

  FILES = [
    "core/protocol",
    "core/model_state",
    "core/errors",
    "core/auth",
    "core/operation",
    "core/response",
    "core/verification",
    "core/router",
    "core/server",
    "services/entity_service",
    "services/transformation_service",
    "services/metadata_service",
    "handlers/system",
    "handlers/inspection",
    "handlers/geometry",
    "handlers/transform",
    "handlers/materials",
    "handlers/attributes",
    "handlers/components",
    "handlers/assembly",
    "handlers/scenes",
    "handlers/init"
  ].freeze

  def load_files!
    FILES.each do |f|
      path = File.join(PLUGIN_DIR, "#{f}.rb")
      load path
    end
    Handlers.register_all
  end

  def reload!
    Server.stop(true) rescue nil
    load File.join(PLUGIN_DIR, "main.rb")
    load_files!
    Server.start(true) rescue nil
    puts "TuSketchupAgent: Extension and modules successfully reloaded."
  end

  def reload_extension
    reload!
  end

  # Initial load of all modules & handlers
  load_files!

  # ==========================================
  # SketchUp Menu & Auto-start
  # ==========================================
  unless file_loaded?(__FILE__)
    menu = UI.menu("Extensions")
    submenu = menu.add_submenu("Tu SketchUp Agent")

    submenu.add_item("Ping / Status") do
      status = Handlers::System.ping_response
      UI.messagebox("Tu SketchUp Agent đang hoạt động.\nServer: #{status[:server]} (#{Server.running? ? 'RUNNING' : 'STOPPED'})\nDev Mode: #{status[:dev_mode] ? 'BẬT' : 'TẮT'}\nOperations: #{Router.registered_commands.length}")
    end

    submenu.add_item("Toggle Dev Mode") do
      Auth.dev_mode = !Auth.dev_mode?
      UI.messagebox("Chế độ Dev Mode: #{Auth.dev_mode? ? 'BẬT (Cho phép execute_ruby)' : 'TẮT (Chặn execute_ruby)'}")
    end

    submenu.add_separator
    submenu.add_item("Create Test Box (1000mm)") do
      Handlers::Geometry.create_box("width" => 1000, "depth" => 1000, "height" => 1000, "name" => "Test Box")
      UI.messagebox("Đã tạo khối hộp 1000 x 1000 x 1000 mm.")
    end

    submenu.add_separator
    submenu.add_item("Start TCP Bridge") { Server.start }
    submenu.add_item("Stop TCP Bridge") { Server.stop }
    submenu.add_separator
    submenu.add_item("Reload Extension") { reload! }

    file_loaded(__FILE__)
  end

  # Auto-start TCP Bridge via timer
  UI.start_timer(0.3, false) do
    Server.start(true) rescue nil
  end
end