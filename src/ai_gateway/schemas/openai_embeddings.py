from __future__ import annotations

import hashlib
import struct
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateEmbeddingsRequest(BaseModel):
    """OpenAI-compatible Embeddings request.

    v1 scope changes:
    - Be permissive to unknown fields (extra="ignore").
    - Add optional `dimensions` to align with OpenAI usage on certain models.
    """

    model_config = ConfigDict(extra="ignore")

    model: str
    input: str | list[str] | list[int] | list[list[int]]
    user: str | None = None
    encoding_format: Literal["float", "base64"] = "float"
    dimensions: int | None = Field(default=None, gt=0)

    @field_validator("model")
    @classmethod
    def _non_empty_model(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("model must be a non-empty string")
        return s

    @field_validator("input")
    @classmethod
    def _validate_input(
        cls, v: str | list[str] | list[int] | list[list[int]]
    ) -> str | list[str] | list[int] | list[list[int]]:
        # Accept the supported types; deeper validation will occur in providers.
        if v is None:
            raise ValueError("input must not be None")
        # quick structural sanity checks to satisfy strict typing without over-validating
        if isinstance(v, list) and v:
            first = v[0]
            if isinstance(first, str):
                if not all(isinstance(x, str) for x in v):
                    raise ValueError(
                        "input list must be all strings when first element is a string"
                    )
                # already a list[str]
            elif isinstance(first, int):
                if not all(isinstance(x, int) for x in v):
                    raise ValueError("input list must be all integers when using list[int] form")
                # already a list[int]
            elif isinstance(first, list):
                # v is list[list[int]]
                if not all(isinstance(x, list) for x in v):
                    raise ValueError("input must be list[list[int]] when using nested lists")
                for sub in v:
                    if not isinstance(sub, list) or not all(isinstance(y, int) for y in sub):
                        raise ValueError("nested lists must contain only integers")
        return v


class EmbeddingItem(BaseModel):
    """Single embedding item."""

    model_config = ConfigDict(extra="forbid")

    object: Literal["embedding"] = "embedding"
    embedding: list[float]
    index: int = Field(ge=0)

    @field_validator("embedding")
    @classmethod
    def _embedding_non_empty(cls, v: list[float]) -> list[float]:
        if not v:
            raise ValueError("embedding must contain at least one float")
        return v


class EmbeddingUsage(BaseModel):
    """Usage accounting for embeddings."""

    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class CreateEmbeddingsResponse(BaseModel):
    """OpenAI-compatible Embeddings response."""

    # Allow forward-compatible extra fields in case upstream adds metadata.
    model_config = ConfigDict(extra="ignore")

    object: Literal["list"] = "list"
    data: list[EmbeddingItem]
    model: str
    usage: EmbeddingUsage

    @field_validator("data")
    @classmethod
    def _data_non_empty(cls, v: list[EmbeddingItem]) -> list[EmbeddingItem]:
        if not v:
            raise ValueError("data must contain at least one EmbeddingItem")
        return v


# Helper utilities that providers can optionally reuse.


def deterministic_vector(text: str, dim: int = 16) -> list[float]:
    """Generate a deterministic small float vector from text using SHA-256.

    The same input yields the same output across runs without relying on RNG.
    Values are in [-1, 1) derived from hashed bytes.
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    floats: list[float] = []
    # Use 4 bytes per float (IEEE 754 single precision) by slicing digest repeatedly.
    # If digest is shorter than needed, keep re-hashing with a counter.
    counter = 0
    buf = h
    while len(floats) < dim:
        # Take 4 bytes at a time to make a float, across the buffer; when exhausted, extend.
        for i in range(0, len(buf), 4):
            if len(floats) >= dim:
                break
            chunk = buf[i : i + 4]
            if len(chunk) < 4:
                # pad deterministically using zeros (rare due to 32-byte digest)
                chunk = (chunk + b"\x00\x00\x00\x00")[:4]
            # Convert to unsigned int, then scale to [-1, 1)
            uint = struct.unpack(">I", chunk)[0]
            # Normalize: map to [0,1), then scale to [-1,1)
            val = (uint / 2**32) * 2.0 - 1.0
            floats.append(val)
        counter += 1
        if len(floats) < dim:
            buf = hashlib.sha256(h + counter.to_bytes(4, "big")).digest()
    return floats


def normalize_input_to_strings(inp: str | list[str] | list[int] | list[list[int]]) -> list[str]:
    """Normalize supported embedding inputs into a list of strings.

    - str -> [str]
    - list[str] -> list[str]
    - list[int] -> [" ".join(str(i) for i in list)]
    - list[list[int]] -> [" ".join(str(i) for i in sublist) for each sublist]
    """
    if isinstance(inp, str):
        return [inp]
    if isinstance(inp, list):
        if not inp:
            return []
        first = inp[0]
        if isinstance(first, str):
            # list[str]
            if not all(isinstance(x, str) for x in inp):
                raise ValueError("input list must be all strings if first element is a string")
            return [x for x in inp if isinstance(x, str)]
        if isinstance(first, int):
            # list[int]
            if not all(isinstance(x, int) for x in inp):
                raise ValueError("input list must be all integers when using list[int] form")
            ints_only: list[int] = [x for x in inp if isinstance(x, int)]
            return [" ".join(str(i) for i in ints_only)]
        if isinstance(first, list):
            # list[list[int]]
            if not all(isinstance(x, list) for x in inp):
                raise ValueError("input must be list[list[int]] when using nested lists")
            collapsed: list[str] = []
            for x in inp:
                if not isinstance(x, list) or not all(isinstance(y, int) for y in x):
                    raise ValueError("nested lists must contain only integers")
                # x is list[int] here
                sub_nums: list[int] = [int(y) for y in x]
                collapsed.append(" ".join(str(i) for i in sub_nums))
            return collapsed
    raise ValueError("unsupported input type for embeddings normalization")
