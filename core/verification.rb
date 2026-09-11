# frozen_string_literal: true

module TuSketchupAgent
  module Verification
    extend self

    CONTRACT_VERSION = 1

    def contract(command:, before_state:, after_state:, transaction:, handler_ok:)
      revision_delta = after_state[:revision].to_i - before_state[:revision].to_i
      committed = transaction[:status].to_s == "committed"
      verified = handler_ok == true && committed && revision_delta == 1

      {
        verification_contract_version: CONTRACT_VERSION,
        requested: true,
        executed: true,
        committed: committed,
        verified: verified,
        command: command.to_s,
        transaction: transaction,
        model_state_transition: {
          before_revision: before_state[:revision],
          after_revision: after_state[:revision],
          revision_delta: revision_delta,
          session_id_unchanged: before_state[:model_session_id].to_s == after_state[:model_session_id].to_s
        }
      }
    end
  end
end
