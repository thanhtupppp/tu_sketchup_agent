# frozen_string_literal: true

require "securerandom"

module TuSketchupAgent
  module ModelState
    extend self

    STATE_VERSION = 1

    @model_object_id = nil
    @model_session_id = nil
    @revision = 0
    @last_change_at = nil

    def reset!
      @model_object_id = nil
      @model_session_id = nil
      @revision = 0
      @last_change_at = nil
    end

    def active_model
      Sketchup.active_model
    end

    def ensure_model!(model = nil)
      model ||= active_model
      raise "Không có model nào đang mở" unless model

      object_id = model.object_id
      if @model_object_id != object_id
        @model_object_id = object_id
        @model_session_id = SecureRandom.uuid
        @revision = 0
        @last_change_at = Time.now.to_i
      end

      model
    end

    def revision(model = nil)
      ensure_model!(model)
      @revision
    end

    def bump_revision(model = nil)
      ensure_model!(model)
      @revision += 1
      @last_change_at = Time.now.to_i
      @revision
    end

    def matches_revision?(expected_revision, model = nil)
      return true if expected_revision.nil?

      ensure_model!(model)
      Integer(expected_revision) == @revision
    rescue ArgumentError, TypeError
      false
    end

    def state(model = nil)
      model = ensure_model!(model)
      {
        state_version: STATE_VERSION,
        model_session_id: @model_session_id,
        model_guid: model.respond_to?(:guid) ? model.guid : nil,
        revision: @revision,
        last_change_at_unix: @last_change_at,
        title: model.title.to_s.empty? ? "Untitled" : model.title.to_s,
        path: model.path.to_s,
        dirty: model.respond_to?(:modified?) ? !!model.modified? : nil
      }
    end
  end

  # Module-level delegates for compatibility and simpler handler access.
  def self.model_state(model = nil)
    ModelState.state(model)
  end

  def self.model_session_id(model = nil)
    ModelState.state(model)[:model_session_id]
  end
end
