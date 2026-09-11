# frozen_string_literal: true

module TuSketchupAgent
  module Handlers
    extend self

    def register_all
      Router.clear_handlers!
      System.register
      Inspection.register
      Geometry.register
      Transform.register
      Materials.register
      Attributes.register
      Components.register
      Assembly.register
      Scenes.register
      puts "TuSketchupAgent: Registered #{Router.registered_commands.length} operations in Router"
    end
  end
end
