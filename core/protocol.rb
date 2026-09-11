# frozen_string_literal: true

module TuSketchupAgent
  HOST = "127.0.0.1" unless const_defined?(:HOST)
  PORT = 9876 unless const_defined?(:PORT)
  TOKEN = "tu-local-secret" unless const_defined?(:TOKEN)
  MAX_DIMENSION_MM = 1_000_000 unless const_defined?(:MAX_DIMENSION_MM)
  PROTOCOL_VERSION = "1.3"
  MIN_COMPATIBLE_PROTOCOL_VERSION = "1.0"
end
