# Config Plan 1 — Root Cause Analysis and Fix Strategy for Settings Failures

Last Updated: 2025-08-02T23:11:00Z

Scope: Analyze failing tests in tests/config/test_config.py, determine exact root causes, and define a minimal, single-edit fix strategy for src/ai_gateway/config/config.py that resolves all failures coherently and aligns with project standards.

## Summary of Failing Tests and Observed Symptoms

1) test_allowed_api_keys_csv_parsing_and_trimming
   - Expectation: ALLOWED_API_KEYS env of " key1 ,key2,  key3 , ," becomes ["key1","key2","key3"].
   - Current behavior: s.ALLOWED_API_KEYS == [].
   - Symptom indicates ALLOWED_API_KEYS is either being ignored or overwritten by another source. No JSONDecodeError anymore, but final field is empty.

2) test_log_level_normalization[debug|INFO|Warning|ERROR]
   - Expectation: LOG_LEVEL normalized to uppercase of input (DEBUG, INFO, WARNING, ERROR).
   - Current behavior: s.LOG_LEVEL == "INFO" regardless of provided value (e.g., "debug"), implying LOG_LEVEL env isn't being applied, likely due to environment source ordering change—env provider maybe not used for other fields.

3) test_invalid_log_level_raises
   - Expectation: LOG_LEVEL="VERBOSE" raises ValueError in validator.
   - Current behavior: DID NOT RAISE, meaning the validator didn't see invalid value, probably because env wasn't applied, default remained "INFO".

4) test_timeout_must_be_positive
   - Expectation: REQUEST_TIMEOUT_S="0" should raise ValueError in model_validator mode="after".
   - Current behavior: DID NOT RAISE, likely because env value didn't reach the model; default remained 30.

5) test_cached_get_settings_returns_same_instance_until_cleared
   - Expectation: After setting os.environ["SERVICE_PORT"]="9000" and cache_clear(), new instance reflects SERVICE_PORT=9000.
   - Current behavior: Still 8000, meaning env provider didn't apply new value post cache clear (or provider not present).

6) test_url_fields_accept_valid_when_provided (previously failing, now passing)
   - Now appears fine; indicates some validators and defaults are okay.

Net observation: After edits, we prevented JSONDecodeError, but we also suppressed the default EnvSettingsSource for non-ALLOWED_API_KEYS fields inadvertently in some iterations, or we returned the wrong set of five sources/ordering causing other env vars not to be applied.

## Root Causes (Precise)

A) ALLOWED_API_KEYS source precedence and exclusivity:
   - We must ensure ALLOWED_API_KEYS is provided ONLY by our custom source and NEVER parsed by default EnvSettingsSource, to avoid JSONDecodeError for CSV/empty strings.
   - Our latest approach introduced _EnvSkipAllowedKeys as a replacement for env_settings to skip ALLOWED_API_KEYS entirely and included our custom _EnvCSVSource.
   - However, ordering was set as: (init_settings, dotenv_settings, _EnvSkipAllowedKeys, _EnvCSVSource, file_secret_settings)
   - This ordering causes two issues:
     1. ALLOWED_API_KEYS: _EnvSkipAllowedKeys runs before _EnvCSVSource, thus ALLOWED_API_KEYS is not included in settings values until later sources. That can be fine, but…
     2. Other fields (LOG_LEVEL, REQUEST_TIMEOUT_S, SERVICE_PORT) depend on a normal env provider behavior. _EnvSkipAllowedKeys is acting as env settings, but it’s custom and must strictly mirror EnvSettingsSource semantics for all fields except ALLOWED_API_KEYS. If our custom __call__ deviates (e.g., missing env_nested_delimiter behavior, or mishandling prepare_field_value), it can result in ignoring other fields or failing to supply them, leading to defaults being used, which matches observed failures.

B) Default env provider missing or mis-ordered:
   - In some iterations we removed env_settings entirely and replaced with _EnvSkipAllowedKeys. That is acceptable ONLY if _EnvSkipAllowedKeys fully delegates to EnvSettingsSource behavior for all non-ALLOWED_API_KEYS fields (including nested/decode behaviors). Our override of __call__ reimplemented the iteration and preparation pipeline, which is fragile and can miss internal behavior of the base class (e.g., environment prefix handling, nested delimiter, complex decoding rules). This likely caused LOG_LEVEL, REQUEST_TIMEOUT_S, SERVICE_PORT to not be populated from env.

C) ALLOWED_API_KEYS value_is_complex handling:
   - For the custom source, we must return a JSON string with value_is_complex=True so default env processing decodes to Python types. That was implemented correctly.
   - But if default env provider runs BEFORE our custom source and sees ALLOWED_API_KEYS, it will attempt to parse raw CSV or empty string as JSON and fail. Therefore, either:
     - Default env provider must run AFTER our custom source, and the custom source must set value_is_complex=True so it short-circuits further decoding; OR
     - Default env must skip ALLOWED_API_KEYS entirely, and the custom source provides it.
   - The safest approach is: include both default env and custom env, but ensure default env NEVER sees ALLOWED_API_KEYS (skip), and custom env provides it.

D) env_ignore_empty semantics:
   - We set env_ignore_empty=True, which is good to prevent empty strings from being treated as values for most fields. This shouldn’t break the behavior, but combined with C and B, might not be the key issue anymore.

## Minimal, Single-Edit Fix Strategy

Goal: Restore correct env behavior for all fields while keeping ALLOWED_API_KEYS parsing robust.

1) Do not override __call__ in _EnvSkipAllowedKeys.
   - Returning a custom __call__ risks diverging from EnvSettingsSource internals.
   - Instead, only override get_field_value to return (None, field_name, False) for ALLOWED_API_KEYS and delegate to super().get_field_value otherwise. This allows the base EnvSettingsSource implementation to prepare values consistently for all other fields (LOG_LEVEL, SERVICE_PORT, REQUEST_TIMEOUT_S, etc.). This will reinstate non-ALLOWED_API_KEYS env processing.

2) Source order must be exactly five sources and standard:
   - Return (init_settings, dotenv_settings, _EnvCSVSource(settings_cls), _EnvSkipAllowedKeys(settings_cls), file_secret_settings)
   - Rationale:
     - _EnvCSVSource first: provides ALLOWED_API_KEYS with value_is_complex=True (JSON string), so downstream sources don’t need to supply ALLOWED_API_KEYS.
     - _EnvSkipAllowedKeys second: default env provider but with ALLOWED_API_KEYS skipped. This ensures the default provider handles all other fields (LOG_LEVEL, SERVICE_PORT, REQUEST_TIMEOUT_S) correctly.
     - No separate env_settings beyond _EnvSkipAllowedKeys to avoid a second EnvSettingsSource that might re-process ALLOWED_API_KEYS.
     - This meets the “exactly five sources” rule and retains default env semantics for everything except ALLOWED_API_KEYS.

3) _EnvCSVSource behavior:
   - For env missing: return (None, field_name, False)
   - For empty string: return ("[]", True)
   - For JSON list string: return (same string, True) after minimal validation
   - For CSV: return (json.dumps(list), True)
   This is already implemented.

4) Keep env_ignore_empty=True in model_config.

5) Validators:
   - LOG_LEVEL validator is correct and will be exercised once default env provider works again.
   - REQUEST_TIMEOUT_S constraint via Field(..., gt=0) combined with model_validator(mode="after") raising on <=0 covers the test.
   - SERVICE_PORT: ensure int cast is preserved in model_validator (already present).
   - ALLOWED_API_KEYS field validator: current logic handles both JSON string and CSV fallback.

This single cohesive edit addresses:
- ALLOWED_API_KEYS parsing becomes consistent and exclusive to our custom source.
- Default env provider behavior is restored for all other fields.
- Tests for normalization and positive timeout will now exercise validators because env assignment works again.

## Acceptance After Fix

Run pytest and expect:
- test_allowed_api_keys_csv_parsing_and_trimming → passes (list parsed from CSV).
- test_log_level_normalization[...] → passes (uppercase value returned).
- test_invalid_log_level_raises → passes (ValueError).
- test_timeout_must_be_positive → passes (ValueError).
- test_cached_get_settings_returns_same_instance_until_cleared → passes (SERVICE_PORT from env reflected after cache_clear()).

## Implementation Notes

Edit src/ai_gateway/config/config.py:
- In settings_customise_sources, return exactly:
  (init_settings, dotenv_settings, cls._EnvCSVSource(settings_cls), _EnvSkipAllowedKeys(settings_cls), file_secret_settings)
- Remove the __call__ override in _EnvSkipAllowedKeys; keep only get_field_value override.
- Ensure no second default env provider (env_settings) is included beyond the skip wrapper.

No other files need changes.

## Risks and Mitigations

- Risk: If tests expect dotenv to override init_settings or vice versa, our ordering preserves standard semantics: init_settings -> dotenv -> env.
- Risk: If ALLOWED_API_KEYS provided via dotenv, our custom source reads os.environ; dotenv provider will have exported env earlier in chain for pydantic reading. However, _EnvCSVSource should not rely on dotenv rewriting os.environ; to remain robust for .env, keep dotenv_settings in the chain before our custom environment sources, which we do.

## Rollback Plan

If unexpected behavior persists:
- Temporarily restore previous ordering and add logging to _EnvCSVSource.get_field_value to verify it is invoked and returns value_is_complex=True for ALLOWED_API_KEYS. Then re-apply the fixed ordering.
