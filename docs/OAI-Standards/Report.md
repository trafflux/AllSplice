# OpenAI Compatibility Report — Universal AI Gateway
Date: 2025-08-03

Purpose: Assess our current OpenAI-compatible schemas against the latest OpenAI Python SDK (openai/openai-python v1.x) and API reference, focusing on Chat Completions and Embeddings. Identify gaps in headers and body field coverage, and provide concrete recommendations to achieve maximum compatibility for “drop-in” OpenAI clients.

Sources consulted (OpenAI official Python SDK repository):
- Library ID: /openai/openai-python (latest; v1.x)
- Evidence snippets extracted from README.md, api.md, helpers.md, CHANGELOG.md via MCP doc fetch
- Notable areas: Chat Completions API, Embeddings API, client options, streaming/events, error headers, request/response structures

Note: OpenAI’s SDK now orients toward the Responses API; Chat Completions remains supported. This report confines scope to Chat Completions and Embeddings, matching our v1 goals.

---

## 1) Current Implementation Summary (repo)

Files reviewed:
- src/ai_gateway/schemas/openai_chat.py
- src/ai_gateway/schemas/openai_embeddings.py
- src/ai_gateway/schemas/openai_models.py

Global style:
- Pydantic models use strict validation and `extra="forbid"` across request and response payloads. This forbids unknown fields and enforces strong typing.

1.1 Chat Completions (openai_chat.py)
- RoleEnum: {"system","user","assistant","tool"}
- ChatMessage: role + content:str (must be non-empty).
- ChatCompletionRequest:
  - Required: model:str, messages:list[ChatMessage]
  - Optional: temperature (0..2), max_tokens (>0), top_p (0..1), n (>=1), stop (str | list[str] | None), presence_penalty, frequency_penalty.
  - Forbids extra fields.
- Choice: index, message:ChatMessage, finish_reason ∈ {"stop","length","content_filter","tool_calls"}
- Usage: prompt_tokens, completion_tokens, total_tokens (>=0)
- ChatCompletionResponse: id, object="chat.completion", created:int epoch, model, choices: list[Choice], usage:Usage
  - Forbids extra fields, choices must be non-empty.

1.2 Embeddings (openai_embeddings.py)
- CreateEmbeddingsRequest:
  - Required: model:str, input: str | list[str] | list[int] | list[list[int]]
  - Optional: user:str | None, encoding_format ∈ {"float","base64"} (default "float")
  - Forbids extra fields.
- CreateEmbeddingsResponse:
  - object="list", data:list[EmbeddingItem], model:str, usage:EmbeddingUsage
- Helper functions: deterministic_vector, normalize_input_to_strings

1.3 Models (openai_models.py)
- Model, ModelPermission, ListResponse[T] (OpenAI-style, strict).

---

## 2) OpenAI Latest Expectations (Python SDK v1.x evidence)

2.1 Headers, Request IDs, Raw/Streaming access
- Clients can access raw HTTP responses and headers via `.with_raw_response` and `.with_streaming_response`.
- Request ID surfaced via `x-request-id`; SDK exposes `response._request_id` (not standard JSON body).
- SDK supports configuration of `timeout` and `max_retries` at client level or per request.
Implication: Server should return request IDs and standard error headers; streaming headers are SDK-handled, not body fields.

2.2 Chat Completions API
- Endpoint: POST /chat/completions
- SDK types include a wide range of message roles and content parts (e.g., function/fn tool calls, tool messages, multi-part content including images/audio in newer models).
- Methods available: create/retrieve/update/list/delete; streaming variants and events defined.
- Samples show role "developer" in examples; SDK also references tool calls, logprobs, and stream options.

Observed fields commonly supported in OpenAI Chat Completions (non-exhaustive):
- model, messages
- temperature, top_p, max_tokens, n, stop
- presence_penalty, frequency_penalty
- user
- logit_bias
- logprobs (+ structured token logprobs fields)
- seed
- tools, tool_choice, function_call (legacy), functions (legacy)
- response_format (JSON/object mode)
- reasoning controls (e.g., reasoning_effort in newer models)
- modalities/audio/image content parts in content for newer omni models
- metadata, store, parallel_tool_calls, top_logprobs (token-level)
- stream, stream_options

Response shape:
- id, object="chat.completion" or chunk types in streaming
- created, model, choices (message {role, content, tool_calls?, function?}, finish_reason), usage
- Logprob structures when requested
- Tool call structures on assistant message choices

2.3 Embeddings API
- Endpoint: POST /embeddings
- Input accepts str or list[str]; SDK also supports token arrays in some contexts; output contains data:list of embedding items, model, usage.
- encoding_format allows base64 or float. Additional parameters sometimes present: dimensions (for some models), user, input_type variations.

2.4 SDK nuance
- The SDK allows “extra_body”, “extra_headers”, “extra_query” on requests. Clients may attach unknown fields. Our `extra="forbid"` will reject such additions.

---

## 3) Compatibility Analysis: Gaps vs Current Schemas

3.1 Strict forbidding of extra fields
- Current: `extra="forbid"` on all request/response schemas.
- Effect: Any OpenAI client sending newer or optional fields (e.g., user, logprobs, seed, tools, tool_choice, response_format, function_call/functions (legacy), metadata, store, stream, stream_options, logit_bias, top_logprobs) will be rejected.
- Risk: High. OpenAI SDK examples and agents often send extra fields.

3.2 Chat Message structure limitations
- Current ChatMessage: only role and content:str. No support for:
  - Multi-part content structures (e.g., content as list with type-tagged parts such as images/audio chunks common in gpt-4o variations).
  - Tool message shape constraints (tool messages often include tool_call_id).
  - Function/Tool call outputs/messages.
  - Roles beyond {system,user,assistant,tool}. SDK snippets reference "developer" role in examples.
- Risk: High for modern clients using tools, images, JSON schema parsing, or multi-modal content.

3.3 ChatCompletionRequest missing commonly used fields
- Missing fields:
  - user
  - logprobs (+ top_logprobs)
  - logit_bias: dict[str,int/float]
  - seed
  - tools (tools/functions legacy), tool_choice
  - function_call/functions (legacy; still used)
  - response_format
  - stream (bool), stream_options
  - metadata, store, parallel_tool_calls
  - reasoning controls (e.g., reasoning_effort)
- Our allowed enums:
  - FinishReasonEnum includes "tool_calls" which is good, but we don’t model tool_calls in message.

3.4 Response shape limitations
- Our Choice.message is ChatMessage (content:str only), missing:
  - tool_calls/function call results in assistant messages
  - refusal fields, logprobs when requested
- Our object literal: "chat.completion" aligns with standard non-stream response. Streaming chunk types not modeled in schemas (acceptable if we do not stream).
- Usage present and aligns, but lack of optional/null fields (e.g., missing total for some providers) can cause mismatch. Our validators require non-empty lists and non-negative ints; OpenAI sometimes returns 0 or omits optional fields; SDK tolerates null/missing using model_fields_set. Because we “forbid extra” and require fields strictly present, we’re less permissive than OpenAI.

3.5 Embeddings gaps
- Request supports input: str | list[str] | list[int] | list[list[int]] which is more permissive than some OpenAI docs; OK.
- Missing commonly used optional fields:
  - dimensions (for certain models)
  - user (we have)
  - input_type variants outside current union (e.g., images/audio not in scope usually for embeddings endpoint; acceptable)
- encoding_format supported matches OpenAI ("float" or "base64"). Good.
- Response shape aligns: object="list", data embedding items, model, usage. Good.

3.6 Headers
- OpenAI clients rely on:
  - Authorization: Bearer <key>
  - Content-Type: application/json
  - The SDK surfaces x-request-id for debugging; ensure we return a unique id header.
- Our middleware includes correlation ID and security headers. Auth header supported. We should ensure we propagate:
  - x-request-id (request_id) header in responses (and in errors).
  - www-authenticate: Bearer on 401.
- Docs show `.with_raw_response` usage and accessing headers. Compatibility requires stable header casing and availability.

3.7 Deprecated/alternate APIs
- SDK features the newer Responses API and many assistants/beta routes. Out of scope for our v1.0, but clients may accidentally hit them. Our router should cleanly 404/405 those paths.

---

## 4) Detailed Gap Table

Headers:
- x-request-id exposure:
  - Current: Our correlation middleware creates/propagates a request id and logging; verify response header name is "x-request-id" to match SDK expectations.
- WWW-Authenticate on 401:
  - Current: In standards; ensure actual handler sets `WWW-Authenticate: Bearer`.

Chat Completions — Request:
- Supported: model, messages, temperature, max_tokens, top_p, n, stop, presence_penalty, frequency_penalty.
- Missing/highly recommended:
  - user
  - logit_bias
  - logprobs, top_logprobs
  - tools, tool_choice
  - functions, function_call (legacy but still used)
  - response_format
  - stream, stream_options
  - seed
  - metadata, store, parallel_tool_calls
  - reasoning_effort (for reasoning models)
- Message content type:
  - Only string content; missing multi-part content blocks for multimodal.
  - Tool/function call structures not modeled in messages.

Chat Completions — Response:
- Supported: id, object, created, model, choices, usage; finish_reason includes tool_calls.
- Missing:
  - choices[].message.tool_calls / function call payloads
  - choices[].logprobs (token logprobs when requested)
  - refusal fields (when applicable in new SDK events; in final ChatCompletion, refusals may fold into message content or separate fields depending on API evolution)
  - Any optional fields that may be null or omitted must be tolerated (we enforce existence and forbid extras).

Embeddings — Request:
- Supported: model, input, user, encoding_format
- Missing:
  - dimensions (commonly used with some models)
- Our input union includes list[int] and list[list[int]] which is permissive; acceptable.

Embeddings — Response:
- Matches OpenAI: object="list", data items with object="embedding", embedding vector, index; model; usage.
- Ensure we tolerate large floats and optional usage fields that could be zero.

---

## 5) Recommendations to Achieve Compatibility

Priority 1 — Be permissive to unknown but valid OpenAI fields
- Change model_config for request models from `extra="forbid"` to `extra="ignore"` (or allow) at least for OpenAI entrypoints. This preserves validation for known types while not rejecting clients sending extra fields such as `user`, `tools`, `response_format`, `seed`, etc.
- Alternatively add large coverage of known fields; however, OpenAI evolves rapidly — ignoring unknown is the safest for broad compatibility.

Priority 2 — Expand Chat schemas to commonly used fields
- ChatMessage:
  - content should accept Union[str, list[TypedParts]] where parts include text, image_url, input_audio, etc., aligned with OpenAI ChatCompletionContentPart types.
  - Add optional tool/function-related fields depending on role:
    - tool messages: tool_call_id
  - Accept roles seen in the SDK: include "developer" (OpenAI examples use it), "function" (legacy), and keep "tool".
- ChatCompletionRequest:
  - Add optional fields:
    - user: str
    - logit_bias: dict[str, int | float]
    - logprobs: bool | int (depending on API; newer supports structured logprobs; at minimum bool)
    - top_logprobs: int | None
    - tools: list[ToolSpec]; tool_choice: Union["none","auto","required", NamedToolChoice]
    - functions: list[FunctionSpec] and function_call (legacy): "none" | "auto" | {name: str}
    - response_format: {"type": "json_object"} | JSON schema options
    - stream: bool; stream_options: {"include_usage": bool, ...}
    - seed: int
    - metadata: dict[str, Any]
    - store: bool
    - parallel_tool_calls: bool
    - reasoning_effort: Literal[...] (if supporting reasoning models)
  - Keep existing fields as-is.

- ChatCompletionResponse:
  - Choice.message to include:
    - content: str | parts[]
    - tool_calls: list[{"type":"function","function":{"name":str,"arguments":str, "parsed_arguments"?:Any}}]
    - function (legacy)
  - Optional choices[].logprobs when requested.
  - usage should remain; allow optional zeros.
  - Maintain object="chat.completion" for non-stream.

Note: If providers cannot produce all these, accept them in request and gracefully ignore or map minimally. For responses, include structures only when applicable.

Priority 3 — Embeddings parity
- Add optional `dimensions: int | None` to CreateEmbeddingsRequest to match OpenAI usage.
- Keep encoding_format support.

Priority 4 — Headers and error behavior
- Ensure response includes `x-request-id` header for all responses (success and error), mapping our correlation/request_id to that name.
- On 401, include `WWW-Authenticate: Bearer`.
- Maintain `Content-Type: application/json; charset=utf-8`.

Priority 5 — Streaming stance
- If streaming is out-of-scope in v1.0, accept `stream` param but return 400 with clear message or process as non-stream; alternatively, ignore `stream` and return a normal response. For best compatibility, accept and ignore unless implementing SSE/chunking.

Priority 6 — Testing
- Add tests with the official OpenAI SDK (mocked base_url) sending typical params:
  - tools/tool_choice
  - response_format={"type":"json_object"}
  - user, seed, logprobs, logit_bias
  - stream=true (expect 200 or handled gracefully)
  - developer role in messages
  - Embeddings with dimensions
- Validate we don’t 422 on extra fields.

---

## 6) Concrete Change Set (Schemas)

6.1 Loosen extra handling for request models
- Change ChatCompletionRequest.model_config from `extra="forbid"` to `extra="ignore"`.
- Change CreateEmbeddingsRequest.model_config similarly.

6.2 Expand ChatMessage
- content: Union[str, list[ContentPart]] where ContentPart includes:
  - {type:"text", text:str}
  - {type:"image_url", image_url:{url:str, detail?:Literal["auto","low","high"]}}
  - {type:"input_audio", audio?:{...}} (optional if we don’t plan multimodal now; at least allow/ignore)
- Add tool_call_id: Optional[str] for tool role messages.
- Add roles: include "developer" and "function" (legacy).

6.3 ChatCompletionRequest new optional fields
- user: Optional[str]
- logit_bias: Optional[dict[str, float]]
- logprobs: Optional[bool] and top_logprobs: Optional[int]
- tools: Optional[list[Tool]]
- tool_choice: Optional[ToolChoice]
- functions: Optional[list[FunctionSpec]] and function_call: Optional[FunctionCallSpec] for legacy
- response_format: Optional[dict[str, Any]] (or structured union)
- stream: Optional[bool] and stream_options: Optional[dict[str, Any]]
- seed: Optional[int]
- metadata: Optional[dict[str, Any]]
- store: Optional[bool]
- parallel_tool_calls: Optional[bool]
- reasoning_effort: Optional[Literal["low","medium","high"]] (tentative)

6.4 ChatCompletionResponse
- Choice.message: expand shape same as ChatMessage.
- Add optional tool_calls: list[FunctionToolCall], optional function (legacy) at message level.
- Add optional logprobs structure on choices when requested.
- Keep finish_reason enum but consider adding "tool_call" vs "tool_calls" variations if needed; current includes "tool_calls" which is fine.

6.5 Embeddings
- Add dimensions: Optional[int] to request.

6.6 Maintain strictness on responses?
- Keep `extra="ignore"` on responses too to avoid breaking clients reading unknown fields we might add later; or retain forbid to keep us honest. Given compatibility goal, prefer ignore.

---

## 7) Risk and Backwards Compatibility

- Loosening extra from forbid→ignore reduces accidental 422s, improving compatibility for diverse clients.
- Adding fields is backward compatible for our providers if we treat them as optional and ignore unsupported ones.
- Expanding message content unions increases model complexity; tests must cover serialization/validation.
- If we accept `functions`/`function_call` legacy, ensure providers either ignore or map to internal tools.

---

## 8) Action Items

A. Schema updates:
- Implement permissive extras on request models.
- Add ChatMessage content union and additional roles.
- Add optional fields listed above for ChatCompletionRequest.
- Expand ChatCompletionResponse structures (tool_calls/logprobs optionally present).
- Add dimensions to Embeddings request.

B. Headers:
- Ensure x-request-id is set on all responses (success/error), mirroring our correlation ID.
- Confirm 401 includes `WWW-Authenticate: Bearer`.

C. Provider mapping:
- In providers/custom, ignore unsupported fields but log presence at DEBUG (without secrets).
- For tool calls: if not implemented, return normal text completions; ensure finish_reason still valid.

D. Tests:
- Add unit tests for schemas to accept new OpenAI fields without 422.
- Add integration tests using OpenAI SDK against our base_url with mocked provider to ensure requests pass and headers are as expected.

---

## 9) Conclusion

Current schemas provide a minimal, strict subset of OpenAI Chat Completions and Embeddings. Due to `extra="forbid"` and limited message/choice structures, many legitimate OpenAI client requests will be rejected (tools, response_format, user, logprobs, etc.). To achieve “universally accessible by any AI agent/app” compatibility, we must:

1) Loosen request model strictness (ignore unknown fields).
2) Add commonly used OpenAI fields to ChatCompletionRequest.
3) Expand message content to support multi-part content and tool/function call structures.
4) Add optional fields (dimensions) to Embeddings.
5) Ensure headers (x-request-id, WWW-Authenticate) and error handling match SDK expectations.

These changes will align our gateway with the de facto OpenAI client behaviors and reduce friction for drop-in adoption while preserving strong typing for known fields.
