"""Chat API routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.api.deps import get_chat_service
from src.models.chat import ChatRequest
from src.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Stream a companion reply as Server-Sent Events.

    Each event is `data: <StreamChunk JSON>\\n\\n`. A TOKEN chunk carries one
    text fragment; the stream always ends with exactly one DONE chunk, or one
    ERROR chunk if generation failed mid-stream.

    Args:
        request: The conversation to reply to.
        chat_service: Injected chat orchestration service.

    Returns:
        A `text/event-stream` response.
    """
    return StreamingResponse(
        chat_service.stream_response(request),
        media_type="text/event-stream",
    )
