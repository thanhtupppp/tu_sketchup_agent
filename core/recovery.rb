# frozen_string_literal: true

module TuSketchupAgent
  module Recovery
    extend self

    CONTRACT_VERSION = 1

    POLICIES = {
      "STALE_MODEL_STATE" => {
        action: "REFRESH_MODEL_STATE",
        retry_safe: false,
        mutation_committed: false,
        retry_after: "refresh_model_state"
      },
      "IDEMPOTENCY_REPLAY" => {
        action: "USE_REPLAYED_RESPONSE",
        retry_safe: false,
        mutation_committed: nil,
        retry_after: "none"
      },
      "IDEMPOTENCY_KEY_REUSE" => {
        action: "CREATE_NEW_REQUEST_ID",
        retry_safe: false,
        mutation_committed: nil,
        retry_after: "new_request_id"
      },
      "IDEMPOTENCY_SESSION_MISMATCH" => {
        action: "REFRESH_MODEL_STATE",
        retry_safe: false,
        mutation_committed: nil,
        retry_after: "refresh_model_state"
      },
      "TRANSACTION_VERIFICATION_FAILED" => {
        action: "REFRESH_MODEL_STATE_AND_INSPECT_RESULT",
        retry_safe: false,
        mutation_committed: nil,
        retry_after: "refresh_model_state"
      },
      "INTERNAL_ERROR" => {
        action: "INSPECT_ERROR_BEFORE_RETRY",
        retry_safe: false,
        mutation_committed: nil,
        retry_after: "inspect_error"
      },
      "UNAUTHORIZED" => {
        action: "CHECK_AUTHENTICATION",
        retry_safe: false,
        mutation_committed: false,
        retry_after: "fix_credentials"
      },
      "NO_ACTIVE_MODEL" => {
        action: "OPEN_OR_ACTIVATE_MODEL",
        retry_safe: false,
        mutation_committed: false,
        retry_after: "ensure_active_model"
      },
      "FORBIDDEN" => {
        action: "CHANGE_ALLOWED_WORKFLOW",
        retry_safe: false,
        mutation_committed: false,
        retry_after: "change_request"
      },
      "UNKNOWN_COMMAND" => {
        action: "USE_SUPPORTED_COMMAND",
        retry_safe: false,
        mutation_committed: false,
        retry_after: "fix_command"
      }
    }.freeze

    def decorate(response)
      return response unless response.is_a?(Hash)
      error = response[:error]
      return response unless error.is_a?(Hash)

      code = error[:code].to_s
      policy = policy_for(code)
      response[:recovery] = {
        contract_version: CONTRACT_VERSION,
        action: policy[:action],
        retry_safe: policy[:retry_safe],
        mutation_committed: policy[:mutation_committed],
        retry_after: policy[:retry_after]
      }
      response
    end

    def policy_for(code)
      POLICIES[code.to_s] || {
        action: "INSPECT_ERROR",
        retry_safe: false,
        mutation_committed: nil,
        retry_after: "inspect_error"
      }
    end
  end

  def self.recovery_for(code)
    Recovery.policy_for(code)
  end

  def self.decorate_recovery(response)
    Recovery.decorate(response)
  end
end
