# frozen_string_literal: true

module TuSketchupAgent
  class Error < StandardError; end
  class AuthenticationError < Error; end
  class ForbiddenError < Error; end
  class DevModeRequiredError < Error; end
  class EntityNotFoundError < Error; end
  class ValidationError < Error; end
  class StaleModelStateError < Error; end
  class TransactionVerificationError < Error; end
end
