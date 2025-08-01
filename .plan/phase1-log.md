Phase 1 scaffolding implemented with constants, settings, and tests. Current pytest run shows failing tests due to ALLOWED_API_KEYS behavior under certain env configurations. The source of persistent failures is twofold:
1) pydantic-settings list parsing: For list-typed fields, pydantic-settings expects JSON by default. When ALLOWED_API_KEYS="" or " key1 ,key2 ", the env provider tries to json.loads and fails before our field-level validator runs. We attempted to normalize via field validators and env_ignore_empty, but JSON decoding still happens in the EnvSettingsSource before our validator, causing SettingsError. This explains the failure in test_allowed_api_keys_csv_parsing_and_trimming.
2) Dev-mode allowance: test_defaults_allow_empty_keys_in_dev_mode sets REQUIRE_AUTH=true, DEVELOPMENT_MODE=true, ALLOWED_API_KEYS="". Our current validator intended to allow empty in dev mode, but due to issue #1, the EnvSettingsSource errors before our allowance logic can apply. That’s why the test still fails.

Concrete implementation state:
- src/ai_gateway/config/constants.py: finalized with API paths, headers, provider identifiers, default timeout, object name.
- src/ai_gateway/config/config.py: BaseSettings model with fields, types, validator scaffolding, and get_settings() with lru_cache. Includes handling for LOG_LEVEL normalization, URL fields, and intended policy for ALLOWED_API_KEYS (allow empty in dev-mode; require non-empty otherwise).
- src/ai_gateway/config/__init__.py: export constants, Settings, get_settings.
- tests/config/test_config.py: tests added per Phase 1 plan. Current failing tests relate to the ALLOWED_API_KEYS environment parsing and dev-mode allowance.

Next step to fully satisfy tests:
- Introduce a custom settings source in Settings.settings_customise_sources to intercept ALLOWED_API_KEYS from environment as a raw string, bypass JSON decoding, and convert it to a CSV-parsed list before reaching pydantic’s list parsing. This is the supported approach in pydantic-settings v2 to override default env behavior for complex types. With this, we’ll:
  - Treat empty string as [].
  - Split CSV on commas, strip whitespace, drop empties.
  - If a valid JSON list is provided, accept it too.
- Keep the validator enforcing policy:
  - If REQUIRE_AUTH=True and DEVELOPMENT_MODE=False and ALLOWED_API_KEYS is empty -> raise.
  - If DEVELOPMENT_MODE=True -> allow empty.
- Re-run tests to green; coverage should remain above threshold.

Given user’s direction, tests were re-run, confirming the above behavior. Implementing the custom source will resolve the JSONDecodeError and let the dev-mode test pass as intended. The repository remains consistent with Phase 1 deliverables except for the final ALLOWED_API_KEYS parsing path, which needs the custom source addition described above to satisfy the tests completely.
