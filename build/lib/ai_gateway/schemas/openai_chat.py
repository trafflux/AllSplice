from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

RoleEnum = Literal["system", "user", "assistant", "tool"]
FinishReasonEnum = Literal["stop", "length", "content_filter", "tool_calls"]


class ChatMessage(BaseModel):
    """
    OpenAI-compatible chat message.
    """

    model_config = ConfigDict(extra="forbid")

    role: RoleEnum
    content: str

    @field_validator("content")
    @classmethod
    def _non_empty_content(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("content must be a non-empty string")
        return s


class ChatCompletionRequest(BaseModel):
    """
    OpenAI-compatible Chat Completions request payload.
    """

    model_config = ConfigDict(extra="forbid")

    model: str
    messages: List[ChatMessage]

    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    top_p: Optional[float] = Field(default=None, ge=0, le=1)
    n: Optional[int] = Field(default=None, ge=1)
    stop: Optional[Union[List[str], str]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None

    @field_validator("model")
    @classmethod
    def _non_empty_model(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("model must be a non-empty string")
        return s

    @field_validator("messages")
    @classmethod
    def _messages_non_empty(cls, v: List[ChatMessage]) -> List[ChatMessage]:
        if not v:
            raise ValueError("messages must contain at least one message")
        return v


class Choice(BaseModel):
    """
    One completion choice.
    """

    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    message: ChatMessage
    finish_reason: FinishReasonEnum


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
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    object: Literal["chat.completion"]
    created: int
    model: str
    choices: List[Choice]
    usage: Usage

    @field_validator("id")
    @classmethod
    def _non_empty_id(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("id must be a non-empty string")
        return s

    @field_validator("created")
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
    def _choices_non_empty(cls, v: List[Choice]) -> List[Choice]:
        if not v:
            raise ValueError("choices must contain at least one item")
        return v
