Plan:
1) Verify and finalize ALLOWED_API_KEYS env parsing in src/ai_gateway/config/config.py so tests are stable and Pylance issues are addressed.
2) Add .plan/phase2-steps.md with concrete steps and acceptance criteria for Phase 2.
3) Implement OpenAI-compatible chat schema models in src/ai_gateway/schemas/openai_chat.py following project standards (strict typing, forbid extra, validators).
4) Add tests in tests/schemas/test_openai_chat.py to cover happy paths and validation errors.
5) Run pytest and iterate until green.

Proposed config adjustments:
- Ensure our EnvSettingsSource-derived handler returns a native Python list for ALLOWED_API_KEYS and flags it as not complex to short-circuit default JSON decoding. This reliably bypasses EnvSettingsSource.decode_complex_value and prevents the default env source from trying JSON first.
- Keep our custom source ordered before the default env source.
- Remove the dynamic subclass wrapper skipping ALLOWED_API_KEYS to eliminate Pylance abstract class warnings. With the native-list return and is_complex=False, the default source will not re-process that field once an earlier source has already provided a value.

Target implementation details:
Inside _EnvCSVSource.get_field_value:
- For ALLOWED_API_KEYS only:
  - If no env set, defer to super().
  - If JSON-like list string, parse to list, trim entries, drop empties; return (list_value, field_name, False).
  - Else treat as CSV: split, trim, drop empties; return (list_value, field_name, False).
- For other fields: super().

Model-level policy validator already present remains unchanged:
- After model init, enforce: if REQUIRE_AUTH and not DEVELOPMENT_MODE and not ALLOWED_API_KEYS: raise ValueError("ALLOWED_API_KEYS must not be empty when REQUIRE_AUTH=True and DEVELOPMENT_MODE=False").

Phase 2 file work to add:
- .plan/phase2-steps.md:
  - Checklist of schema tasks, acceptance criteria aligned to PRD-1.0 and project standards.
- src/ai_gateway/schemas/openai_chat.py:
  - RoleEnum = Literal["system","user","assistant","tool"]
  - FinishReasonEnum = Literal["stop","length","content_filter","tool_calls"]
  - ChatMessage Model:
    - role: RoleEnum
    - content: str (non-empty, strip whitespace in validator)
    - model_config = ConfigDict(extra="forbid")
  - ChatCompletionRequest:
    - model: str (non-empty)
    - messages: list[ChatMessage] (min length ≥ 1)
    - temperature: float | None = Field(None, ge=0, le=2)
    - max_tokens: int | None = Field(None, gt=0)
    - top_p: float | None = Field(None, ge=0, le=1)
    - n: int | None = Field(None, ge=1)
    - stop: list[str] | str | None
    - presence_penalty: float | None
    - frequency_penalty: float | None
    - model_config = ConfigDict(extra="forbid")
  - Choice:
    - index: int = Field(ge=0)
    - message: ChatMessage
    - finish_reason: FinishReasonEnum
    - model_config = ConfigDict(extra="forbid")
  - Usage:
    - prompt_tokens: int = Field(ge=0)
    - completion_tokens: int = Field(ge=0)
    - total_tokens: int = Field(ge=0)
    - model_config = ConfigDict(extra="forbid")
  - ChatCompletionResponse:
    - id: str (non-empty)
    - object: Literal["chat.completion"]
    - created: int (epoch seconds; validator ensures non-negative int)
    - model: str
    - choices: list[Choice] (min length ≥ 1)
    - usage: Usage
    - model_config = ConfigDict(extra="forbid")
- tests/schemas/test_openai_chat.py:
  - Test minimal valid ChatCompletionRequest.
  - Test ChatCompletionResponse with fixed object value and int created.
  - Test invalid roles, extra fields, empty content, created not int, stop types, etc.

Request to proceed:
I will:
- Edit src/ai_gateway/config/config.py to return native lists with is_complex=False and remove the dynamic wrapper.
- Create .plan/phase2-steps.md with the step-by-step checklist and acceptance criteria.
- Add schemas and tests.

Confirm if you want me to implement these changes now. Once applied, I will run pytest to verify all tests pass.
