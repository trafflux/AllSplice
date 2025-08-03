from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RoleEnum = Literal["system", "user", "assistant", "tool", "developer", "function"]
FinishReasonEnum = Literal["stop", "length", "content_filter", "tool_calls"]


class ChatMessage(BaseModel):
    """
    OpenAI-compatible chat message.

    v1 scope (high-impact):
    - Allow developer and function roles (legacy compat).
    - Content may be a simple string or minimal typed parts: text | image_url.
    - tool_call_id supported for tool messages.
    """

    # Be permissive to allow OpenAI clients to send additional properties on messages.
    model_config = ConfigDict(extra="ignore")

    role: RoleEnum

    # Minimal content parts for v1
    # - str OR list of parts with {type: "text", text: str} or {type: "image_url", image_url: {url: str}}
    content: str | list[dict[str, Any]]

    # For tool/function message association (common in OpenAI tool flows)
    tool_call_id: str | None = None

    @field_validator("content")
    @classmethod
    def _validate_content(cls, v: str | list[dict[str, Any]]) -> str | list[dict[str, Any]]:
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("content must be a non-empty string")
            return v
        if isinstance(v, list):
            # Soft validation: ensure it's a list of dicts with at least a type or text/image_url
            for part in v:
                if not isinstance(part, dict):
                    raise ValueError("content parts must be objects")
                # Minimal guardrails without over-constraining:
                if "type" not in part or ("text" not in part and "image_url" not in part):
                    raise ValueError(
                        "content part must include 'type' or payload like 'text'/'image_url'"
                    )
            return v
        raise ValueError("content must be a string or list of content parts")


class ChatCompletionRequest(BaseModel):
    """
    OpenAI-compatible Chat Completions request payload.

    v1 scope changes:
    - Be permissive to unknown fields (extra="ignore") to accept fast-evolving SDK params.
    - Add high-impact optional fields commonly sent by OpenAI clients.
    """

    model_config = ConfigDict(extra="ignore")

    model: str
    messages: list[ChatMessage]

    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    top_p: float | None = Field(default=None, ge=0, le=1)
    n: int | None = Field(default=None, ge=1)
    stop: list[str] | str | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None

    # High-impact additions for v1 compatibility
    user: str | None = None
    logit_bias: dict[str, float] | None = None
    logprobs: bool | None = None
    top_logprobs: int | None = None
    # tool/functions legacy and current tool selector
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    functions: list[dict[str, Any]] | None = None
    function_call: str | dict[str, Any] | None = None
    response_format: dict[str, Any] | None = None
    stream: bool | None = None
    stream_options: dict[str, Any] | None = None
    seed: int | None = None
    metadata: dict[str, Any] | None = None
    store: bool | None = None
    parallel_tool_calls: bool | None = None

    @field_validator("model")
    @classmethod
    def _non_empty_model(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("model must be a non-empty string")
        return s

    @field_validator("messages")
    @classmethod
    def _messages_non_empty(cls, v: list[ChatMessage]) -> list[ChatMessage]:
        if not v:
            raise ValueError("messages must contain at least one message")
        return v


class Choice(BaseModel):
    """
    One completion choice.

    Phase 6: allow optional response-side enrichments for maximal parity:
    - logprobs: optional opaque structure (provider-dependent), included when requested/available.
    """

    model_config = ConfigDict(extra="ignore")

    index: int = Field(ge=0)
    message: ChatMessage
    finish_reason: FinishReasonEnum
    # Optional token logprobs payload (structure varies by provider / SDK evolution)
    logprobs: dict[str, Any] | None = None


class Usage(BaseModel):
    """
    Token usage accounting.
    """

    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class ChatCompletionResponse(BaseModel):
    """
    OpenAI-compatible Chat Completions response payload.

    v1 scope changes:
    - Allow extra fields for forward compatibility (e.g., SDK may surface additional metadata).

    Phase 6:
    - Allow optional tool_calls on assistant messages by permitting extra fields on ChatMessage (already allowed)
      and tolerate provider-included tool call payloads via extra="ignore" across response models.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    object: Literal["chat.completion"]
    created: int
    model: str
    choices: list[Choice]
    usage: Usage

    @field_validator("id")
    @classmethod
    def _non_empty_id(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("id must be a non-empty string")
        return s

    @field_validator("created", mode="before")
    @classmethod
    def _created_epoch_int(cls, v: int) -> int:
        # Pydantic may pass bools as ints; ensure strict int and non-negative
        if type(v) is not int:
            raise ValueError("created must be an integer epoch timestamp")
        if v < 0:
            raise ValueError("created must be a non-negative integer epoch timestamp")
        return v

    @field_validator("choices")
    @classmethod
    def _choices_non_empty(cls, v: list[Choice]) -> list[Choice]:
        if not v:
            raise ValueError("choices must contain at least one item")
        return v
