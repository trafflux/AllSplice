from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class ModelPermission(BaseModel):
    """OpenAI-compatible Model permission object."""

    model_config = ConfigDict(extra="forbid")

    id: str
    object: Literal["model_permission"] = "model_permission"
    created: int = Field(ge=0)

    allow_create_engine: bool
    allow_sampling: bool
    allow_logprobs: bool
    allow_search_indices: bool
    allow_view: bool
    allow_fine_tuning: bool

    organization: str | None = None
    group: str | None = None
    is_blocking: bool

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
        if type(v) is not int:
            raise ValueError("created must be an integer epoch timestamp")
        if v < 0:
            raise ValueError("created must be non-negative")
        return v


class Model(BaseModel):
    """OpenAI-compatible Model object."""

    model_config = ConfigDict(extra="forbid")

    id: str
    object: Literal["model"] = "model"
    created: int = Field(ge=0)
    owned_by: str
    permission: list[ModelPermission]
    root: str | None = None
    parent: str | None = None

    @field_validator("id")
    @classmethod
    def _non_empty_id(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("id must be a non-empty string")
        return s

    @field_validator("owned_by")
    @classmethod
    def _non_empty_owned_by(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("owned_by must be a non-empty string")
        return s

    @field_validator("permission")
    @classmethod
    def _permission_non_empty(cls, v: list[ModelPermission]) -> list[ModelPermission]:
        if not v:
            raise ValueError("permission must contain at least one item")
        return v

    @field_validator("created", mode="before")
    @classmethod
    def _created_epoch_int(cls, v: int) -> int:
        if type(v) is not int:
            raise ValueError("created must be an integer epoch timestamp")
        if v < 0:
            raise ValueError("created must be non-negative")
        return v


class ListResponse(BaseModel, Generic[T]):
    """OpenAI-compatible list wrapper."""

    model_config = ConfigDict(extra="forbid")

    object: Literal["list"] = "list"
    data: list[T]

    @field_validator("data")
    @classmethod
    def _data_non_empty(cls, v: list[T]) -> list[T]:
        if not v:
            raise ValueError("data must contain at least one item")
        return v
