# Phase 2 — Schemas and Config Stabilization

Status: Planned

Scope:
- Finalize ALLOWED_API_KEYS env parsing via custom EnvSettingsSource returning native lists with is_complex=False, remove wrapper.
- Implement OpenAI-compatible chat schemas.
- Add tests for schemas.
- Ensure config tests pass consistently.

Checklist:
1) Config Stabilization
   - Modify _EnvCSVSource.get_field_value to return native Python list for ALLOWED_API_KEYS and set is_complex to False to bypass default JSON decoding.
   - Ensure custom source precedes default EnvSettingsSource in settings_customise_sources ordering.
   - Remove the dynamic wrapper class that skipped ALLOWED_API_KEYS to avoid Pylance abstract warnings.
   - Keep model-level policy validator to enforce non-empty ALLOWED_API_KEYS when REQUIRE_AUTH=True and DEVELOPMENT_MODE=False.
   - Run tests/config/test_config.py and confirm green.

2) Schemas — OpenAI Chat Models
   - Create src/ai_gateway/schemas/openai_chat.py with strict Pydantic models:
     - RoleEnum = Literal["system", "user", "assistant", "tool"]
     - FinishReasonEnum = Literal["stop", "length", "content_filter", "tool_calls"]
     - ChatMessage: role: RoleEnum; content: str (non-empty, strip); extra=forbid
     - ChatCompletionRequest:
         model: str (non-empty)
         messages: list[ChatMessage] (min length ≥ 1)
         temperature: float|None (0..2)
         max_tokens: int|None (>0)
         top_p: float|None (0..1)
         n: int|None (≥1)
         stop: list[str] | str | None
         presence_penalty: float|None
         frequency_penalty: float|None
         extra=forbid
     - Choice: index: int (≥0), message: ChatMessage, finish_reason: FinishReasonEnum, extra=forbid
     - Usage: prompt_tokens, completion_tokens, total_tokens: int (≥0), extra=forbid
     - ChatCompletionResponse:
         id: str (non-empty)
         object: Literal["chat.completion"]
         created: int (epoch seconds, non-negative)
         model: str
         choices: list[Choice] (min length ≥ 1)
         usage: Usage
         extra=forbid
   - All public models fully typed, with validators for content trimming and created validation.

3) Tests — Schemas
   - Create tests/schemas/test_openai_chat.py
     - Validate minimal ChatCompletionRequest with one message passes.
     - Validate ChatCompletionResponse shape, object fixed value, created int, enums enforced.
     - Invalid cases: extra fields rejected, invalid role value, empty content, negative created, wrong stop types, negative indices or token counts.

4) Quality and Standards
   - Strict typing; mypy compliance expected (project uses strict settings).
   - Extra=forbid on all schema models.
   - Docstrings on public classes.
   - Keep cyclomatic complexity low; functions small and cohesive.

Acceptance Criteria:
- All config tests pass, including CSV parsing/whitespace trimming test.
- New schemas implemented and covered by tests.
- tests/schemas/test_openai_chat.py green with pytest.
- Overall test suite remains green.

Notes:
- Secrets and API keys must never be logged.
- Config behavior: empty ALLOWED_API_KEYS allowed only when DEVELOPMENT_MODE=True or REQUIRE_AUTH=False.
