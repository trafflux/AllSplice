# Config Plan 1 — Root Cause Analysis and Minimal Fix Strategy

Last Updated: 2025-08-02T23:18:00Z

Context: tests/config/test_config.py shows clustered failures around Settings env parsing, notably ALLOWED_API_KEYS handling and other env-driven fields (LOG_LEVEL, REQUEST_TIMEOUT_S, SERVICE_PORT). The objective is to fix all by a single coherent change to settings sources precedence without relying on a real .env file.

## Facts from Tests (No reliance on real .env)

- Tests use a helper env_vars context manager to set os.environ for the duration of a test. Therefore, our settings must read os.environ directly during initialization. No real .env is needed or expected.
- Failures previously included JSONDecodeError when ALLOWED_API_KEYS was "" or CSV. That’s resolved by custom handling but now other fields are not being applied (LOG_LEVEL remains INFO, REQUEST_TIMEOUT_S default not overridden, SERVICE_PORT unchanged after cache clear), indicating our default env provider behavior was disrupted.

## Exact Failures and Immediate Causes

1) ALLOWED_API_KEYS CSV/empty parsing
   - Expectation: CSV " key1 ,key2,  key3 , ," -> ["key1","key2","key3"]; empty string -> [] (allowed when REQUIRE_AUTH=false or DEVELOPMENT_MODE=true).
   - Cause (historical): default EnvSettingsSource tries json.loads("") or on CSV → JSONDecodeError.
   - Resolution approach: provide ALLOWED_API_KEYS exclusively via a custom env source that returns a JSON list string and marks value_is_complex=True; ensure the default env provider never attempts to parse ALLOWED_API_KEYS.

2) LOG_LEVEL normalization and invalid raises
   - Expectation: Input variants normalize to uppercase; invalid ("VERBOSE") raises ValueError.
   - Observed: LOG_LEVEL stays at default "INFO" and invalid does not raise, meaning the env value was not applied at all.
   - Cause: Our replacement of the default env provider with a custom wrapper (__call__ override) likely bypassed internal preparation, so other fields from os.environ didn’t propagate.

3) REQUEST_TIMEOUT_S positive enforcement and SERVICE_PORT cache-clear behavior
   - Expectation: REQUEST_TIMEOUT_S="0" raises; SERVICE_PORT reflects new env after get_settings.cache_clear().
   - Observed: No exception and still 8000 after cache clear, meaning env inputs weren’t read by the default provider.
   - Same cause as (2): default env semantics were broken by our wrapper.

## Root Cause

Our attempt to block the default EnvSettingsSource from parsing ALLOWED_API_KEYS by replacing env_settings with a custom provider that re-implements __call__ inadvertently suppressed or altered default handling for all other fields. This led to other env vars (LOG_LEVEL, REQUEST_TIMEOUT_S, SERVICE_PORT) not being read/applied during tests.

## Minimal Single-Edit Fix Strategy

Goal: Restore normal env handling for all fields, while handling ALLOWED_API_KEYS via a custom source that avoids JSONDecodeError for CSV/empty strings.

Single change (in Settings.settings_customise_sources):

- Return exactly five sources in this strict order:
  1) init_settings
  2) dotenv_settings
  3) cls._EnvCSVSource(settings_cls)          # custom handler for ALLOWED_API_KEYS only
  4) _EnvSkipAllowedKeys(settings_cls)        # default EnvSettingsSource-like provider that skips ALLOWED_API_KEYS
  5) file_secret_settings

Design notes:
- _EnvCSVSource must ONLY intercept ALLOWED_API_KEYS and return (json-string, value_is_complex=True) for "", JSON list string, or CSV; otherwise delegate to super().
- _EnvSkipAllowedKeys must ONLY override get_field_value for ALLOWED_API_KEYS to return (None, field_name, False), and otherwise call super().get_field_value. Do NOT override __call__; let EnvSettingsSource implement all preparation/decoding logic for all other fields.
- env_ignore_empty=True in model_config remains to avoid empty strings being treated as real values by the default provider for non-list fields.

Why this works:
- The custom source runs before the default env and provides a complex value for ALLOWED_API_KEYS. Even if the default provider ran later, our skip source ensures it never returns ALLOWED_API_KEYS. All other fields (LOG_LEVEL, REQUEST_TIMEOUT_S, SERVICE_PORT) are now handled by normal default provider logic (via the skip wrapper that fully delegates to super()).
- Tests use os.environ directly; both sources consult os.environ via the base class code paths, so no real .env is needed.

## Validators Sanity Check

- LOG_LEVEL validator: correct; will be invoked once env is correctly applied.
- REQUEST_TIMEOUT_S > 0: enforced by Field(gt=0) and by model_validator to raise on <= 0 — test expects exception, satisfied once env is applied.
- SERVICE_PORT: int cast preserved in model_validator; after cache_clear(), the new instance reads the new env.
- ALLOWED_API_KEYS field validator: robust to JSON string (from custom source) or CSV strings; returns trimmed list.

## Acceptance Criteria After Fix

- ALLOWED_API_KEYS from CSV → list ["key1","key2","key3"]; empty OK under tests that set REQUIRE_AUTH=false or DEVELOPMENT_MODE=true.
- LOG_LEVEL normalization param tests pass; invalid raises.
- REQUEST_TIMEOUT_S=0 raises ValueError.
- SERVICE_PORT updates after get_settings.cache_clear() in test.

## Implementation Checklist (single edit)

- In settings_customise_sources: return (init_settings, dotenv_settings, cls._EnvCSVSource(settings_cls), _EnvSkipAllowedKeys(settings_cls), file_secret_settings).
- Ensure _EnvSkipAllowedKeys ONLY overrides get_field_value; remove any __call__ override if present.
- Ensure _EnvCSVSource returns "[]", or a validated JSON list string, or json.dumps(list) for CSV, with value_is_complex=True; for non-target fields delegate to super().
