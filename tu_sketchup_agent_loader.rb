# File này có thể được copy ra thư mục Plugins cha:
# C:\Users\<Username>\AppData\Roaming\SketchUp\SketchUp 2026\SketchUp\Plugins\tu_sketchup_agent.rb
# để SketchUp tự động nhận diện và tải extension khi khởi động.

require "sketchup.rb"
require "extensions.rb"

module TuSketchupAgent
  unless file_loaded?(__FILE__)
    extension = SketchupExtension.new("Tu SketchUp Agent", File.join(__dir__, "tu_sketchup_agent", "main.rb"))
    extension.description = "AI Agent MCP Bridge for SketchUp 2026 (Connects Antigravity, Cursor, Claude to SketchUp)."
    extension.version     = "1.0.0"
    extension.creator     = "Tu"
    extension.copyright   = "2026"
    
    Sketchup.register_extension(extension, true)
    file_loaded(__FILE__)
  end
end
