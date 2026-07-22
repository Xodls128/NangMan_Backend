from .models import ChatMessage
from .moderation import PROFANITY_REJECT_MESSAGE, contains_profanity


def validate_user_chat_content(raw: str) -> tuple[str | None, str | None]:
    """
    유저 채팅 본문 검증. (정제된 텍스트, 오류 메시지) 반환.
    오류가 있으면 text는 None.
    """
    text = (raw or '').strip()
    if not text:
        return None, '메시지 내용을 입력하세요.'
    if len(text) > ChatMessage.MAX_CONTENT_LENGTH:
        return None, f'메시지는 {ChatMessage.MAX_CONTENT_LENGTH}자까지 가능합니다.'
    if contains_profanity(text):
        return None, PROFANITY_REJECT_MESSAGE
    return text, None
