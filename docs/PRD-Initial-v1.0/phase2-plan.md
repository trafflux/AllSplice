Plan:
1) Verify and finalize ALLOWED_API_KEYS env parsing in src/ai_gateway/config/config.py so tests are stable and Pylance issues are addressed.
2) Add .plan/phase2-steps.md with concrete steps and acceptance criteria for Phase 2.
3) Implement OpenAI-compatible chat schema models in src/ai_gateway/schemas/openai_chat.py following project standards (strict typing, forbid extra, validators).
4) Add tests in tests/schemas/test_openai_chat.py to cover happy paths and validation errors.
5) Run pytest and iterate until green.

Current status (updated after comparison with repo):
- ALLOWED_API_KEYS parsing: Implemented via custom env sources in config.py (_EnvCSVSource + _EnvSkipAllowedKeys). Functionally complete; resolves prior JSON decoding issues. If any tests assumed native-list return, align tests or optionally change to native list with is_complex=False (non-functional difference).
- Schemas: src/ai_gateway/schemas/openai_chat.py implemented and used by providers/routes; strict typing and forbid extra present.
- Tests: tests/schemas/test_openai_chat.py exists and covers happy and error paths.

Proposed config adjustments (optional if tests require):
- Alternative: Ensure custom env source returns a native Python list for ALLOWED_API_KEYS with is_complex=False to bypass complex-json decoding entirely. This is equivalent in effect to the current JSON-normalized path but may simplify test assumptions.

Target implementation details (retained as reference):
Inside _EnvCSVSource.get_field_value:
- For ALLOWED_API_KEYS only:
  - If no env set, defer to super().
  - If JSON-like list string, parse to list, trim entries, drop empties; return value such that downstream decodes cleanly.
  - Else treat as CSV: split, trim, drop empties.

Model-level policy validator remains:
- If REQUIRE_AUTH and not DEVELOPMENT_MODE and ALLOWED_API_KEYS is empty → raise ValueError("ALLOWED_API_KEYS must not be empty when REQUIRE_AUTH=True and DEVELOPMENT_MODE=False").

Pending items:
- Create .plan/phase2-steps.md (documentation checklist).
- Confirm test expectations (if any) align with standardized error payloads from global handlers.

Acceptance criteria:
- Pytest green with stable ALLOWED_API_KEYS parsing and policy behavior.
- OpenAI chat schema validated; forbid extra; correct enums/constraints; tests cover happy/negative cases.
- No Pylance/mypy issues related to settings sources.
