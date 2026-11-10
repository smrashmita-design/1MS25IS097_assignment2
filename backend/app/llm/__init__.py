"""Google Gemini integration layer.

Everything model-specific lives behind :class:`GeminiClient` so the agent loop
never imports the ``google-genai`` SDK directly. Swapping the provider is a
matter of implementing :class:`LLMClient`.
"""

from __future__ import annotations

from app.llm.client import (
    LLMClient,
    LLMError,
    ModelTurn,
    ToolCall,
)

__all__ = ["LLMClient", "LLMError", "ModelTurn", "ToolCall"]
