# frozen_string_literal: true

module TuSketchupAgent
  module Auth
    extend self

    @dev_mode = false

    def dev_mode?
      ENV["TU_SKETCHUP_DEV_MODE"] == "1" || @dev_mode == true
    end

    def dev_mode=(val)
      @dev_mode = !!val
    end

    def verify_token(token)
      token.to_s == TuSketchupAgent::TOKEN
    end
  end

  # Module-level delegates for backward compatibility
  def self.dev_mode?
    Auth.dev_mode?
  end

  def self.dev_mode=(val)
    Auth.dev_mode = val
  end
end
