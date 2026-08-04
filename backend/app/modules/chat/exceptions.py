class ChatError(Exception):
    code = "chat_error"

    def __init__(self, message: str = "会话处理失败") -> None:
        super().__init__(message)
        self.message = message


class ConversationNotFoundError(ChatError):
    code = "conversation_not_found"

    def __init__(self) -> None:
        super().__init__("会话不存在或已被删除")


class MessageNotFoundError(ChatError):
    code = "message_not_found"

    def __init__(self) -> None:
        super().__init__("消息不存在或已被删除")


class ChatValidationError(ChatError):
    code = "chat_validation_error"


class LlmConfigurationError(ChatError):
    code = "llm_configuration_error"


class LlmProviderError(ChatError):
    code = "llm_provider_error"
