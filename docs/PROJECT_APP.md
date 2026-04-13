# DichVuCong AI Assistant — Application Improvement Tasks

**Version 1.0 | Created: 2026-04-13**

This file tracks application-quality tasks separate from the core
pipeline tasks in PROJECT_STATUS.md. These tasks focus on demo
readiness, documentation requirements, and user experience.

## Priority Legend
- **Critical** — required for the demo to function end-to-end
- **High** — required by the project requirements document
- **Medium** — improves quality and impression significantly

## Task Index
| ID | Title | Priority | Status |
|---|---|---|---|
| TASK-APP-01 | Eager model loading | High | 📋 Not Started |
| TASK-APP-02 | Form fill end-to-end | Critical | 📋 Not Started |
| TASK-APP-03 | Authentication gate | High | 📋 Not Started |
| TASK-APP-04 | Streaming speed | Medium | 📋 Not Started |
| TASK-APP-05 | UI error messages | High | 📋 Not Started |
| TASK-APP-06 | Loading indicators | Medium | 📋 Not Started |
| TASK-APP-07 | Citation bolding | Medium | 📋 Not Started |
| TASK-APP-08 | Use case documentation | High | 📋 Not Started |
| TASK-APP-09 | API documentation | High | 📋 Not Started |
| TASK-APP-10 | Performance baseline | Medium | 📋 Not Started |
| TASK-APP-11 | README.md | Critical | 📋 Not Started |
| TASK-APP-12 | Installation + User guides | High | 📋 Not Started |
| TASK-APP-13 | Fix image upload (widget + procedure pages) | Critical | 📋 Not Started |
| TASK-APP-14 | Procedures plan API endpoint | High | 📋 Not Started |
| TASK-APP-15 | Conversation history compaction | Medium | 📋 Not Started |

---

## TASK-APP-01: Eager model loading — eliminate bge-m3 cold start

**Priority:** High

### Goal

The first chat message after server start takes 2–5 minutes because
`EmbedderService` initialises `SentenceTransformer("BAAI/bge-m3")` lazily
on the first call to `_embed_bge_m3()`. The model is not referenced anywhere
in the FastAPI lifespan function — it is created on demand when the first
`rag_fn` call triggers `QdrantService → EmbedderService._embed_bge_m3()`.
For a demo, a 2–5 minute hang on the first user message is unacceptable.

Fixing this reduces the first-request latency to near-zero (after server
startup completes). The fix is confined to the lifespan block in `main.py`
and a fallback UX message in `ChatWidget.tsx`.

### Inputs

- `backend/app/main.py` — lifespan function (currently only initialises
  MinIO; lines 28–50). The `yield` point is line 49. Add before `yield`.
- `backend/app/services/embedder.py` — `EmbedderService.__init__` sets
  `self._st_model = None` (line 46); the model is loaded on first call to
  `_embed_bge_m3()` (line 68). `EmbedderService()` can be called at
  startup to force the load.
- `backend/app/dependencies.py` — check whether a shared `EmbedderService`
  singleton is exposed via a dependency function that `main.py` can call.
  If no singleton exists, instantiate directly.
- `frontend/src/components/chat/ChatWidget.tsx` — `handleSend` callback
  (lines 63–105). The loading state is currently just `<LoadingDots />`
  with no elapsed-time awareness.

### Outputs

1. `backend/app/main.py` — lifespan startup block calls
   `EmbedderService()` (or invokes a dummy embed call) to force model load
   before `yield`. Logs `"Embedding model loaded and ready."` at INFO level.
   If bge-m3 load fails (model files absent, CUDA OOM), catches the
   exception and logs a WARNING rather than crashing startup — the OpenAI
   fallback will handle live requests.
2. `frontend/src/components/chat/ChatWidget.tsx` — `handleSend` starts a
   `setTimeout` at 3 000 ms. If the first response chunk has not arrived by
   that deadline, the assistant message bubble is updated to show the
   waiting message `"Đang khởi động hệ thống AI, vui lòng chờ giây lát…"`
   instead of just `<LoadingDots />`. The timeout is cleared as soon as the
   first chunk arrives.

### Definition of Done

- [ ] `EmbedderService` is constructed inside the lifespan startup block
      in `main.py`, before `yield`
- [ ] Server logs `"Embedding model loaded and ready."` (structlog INFO)
      at startup before accepting requests, visible in `docker compose logs`
- [ ] First chat message after a cold server start responds within 30 s
      once the server readiness log line has appeared (model pre-loaded)
- [ ] If bge-m3 fails to load at startup, the server still starts and
      the warning is logged — the OpenAI fallback path is not broken
- [ ] `ChatWidget.tsx` shows the Vietnamese waiting message when the first
      response chunk takes more than 3 seconds to arrive
- [ ] The waiting message clears correctly when the first chunk arrives

### Notes / Constraints

- `EmbedderService` has no module-level singleton. Calling `EmbedderService()`
  in the lifespan creates a fresh instance. If the rest of the application
  creates its own instance lazily, there will be two separate model loads.
  Introduce a module-level `_embedder_svc` singleton in `embedder.py` and
  a `get_embedder()` factory (same pattern as `_get_qdrant()` in `rag.py`)
  so the lifespan and the worker share the same loaded instance.
- Do not call `asyncio.run_in_executor` inside the lifespan without an
  awaitable context — use `asyncio.get_event_loop().run_in_executor(None,
  EmbedderService)` or simply call the constructor synchronously since the
  lifespan is an `async` function.
- On Windows with no GPU, model load takes ~2–4 minutes. Startup will block
  during this time. This is acceptable — the server is not ready until the
  model is warm.
- The 3-second timeout in `ChatWidget.tsx` is a fallback for cases where the
  server is running but the model was not pre-loaded (e.g., `EMBEDDING_BACKEND
  = openai`). Do not show the message on every request — only on the first
  message in a session or when `isStreaming` transitions from `false` to
  `true` and no chunk has arrived within the threshold.

---

## TASK-APP-02: Wire form fill end-to-end for TTHC-001

**Priority:** Critical

### Goal

TTHC-001 (Đăng ký thường trú) must demonstrate the complete citizen
journey end-to-end:

1. User uploads CCCD image → OCR extracts `PersonalData`
2. User asks to fill the registration form in chat
3. Router classifies intent → `execution_plan: ["ocr_fn", "form_filler_fn"]`
4. `form_filler_fn` fills available fields, stores filled PDF in MinIO `tmp/`
5. Synthesizer detects `form_fill_complete=True` → response mode is
   `form_fill_complete`
6. **The filled form path is surfaced via SSE so the frontend can render
   a download button**
7. User clicks download → browser receives the PDF

This is the most important demo use case for an application project.
Currently, step 6 is missing: `synthesizer_node` returns `response_metadata`
with `mode`, `scope_used`, `scope_notice_included`, and `rag_confidence` —
but `filled_form_path` is never included. The `GET /api/v1/documents/download`
endpoint does not exist. The `ChatWidget.tsx` has no code to render a
download button.

### Inputs

- `backend/app/agents/nodes/synthesizer.py` — `synthesizer_node` returns
  `response_metadata` dict (lines 265–274). The `form_fill_complete` branch
  builds context from `_build_context()` (lines 152–165) but does not
  include `filled_form_path` in `response_metadata`.
- `backend/app/api/v1/chat.py` — `generate()` SSE generator (lines 166–174).
  Streams `final_response` word-by-word, then sends `response_metadata` in a
  single `metadata` event. Currently `response_metadata` does not carry
  `filled_form_path`.
- `backend/app/api/v1/forms.py` — `GET /filled/{file_path}` stub at line 111
  raises `NotImplementedError`. This is the natural home for a download
  endpoint, or add a new endpoint to `documents.py`.
- `backend/app/services/storage_service.py` — `StorageService.download(path)`
  returns bytes. Use this to serve the PDF file.
- `frontend/src/components/chat/ChatWidget.tsx` — `handleSend` processes
  `metadata` events (line 87). Currently only extracts `metadata.citations`.
  No handling for `metadata.filled_form_path`.
- `frontend/src/lib/api/client.ts` — `streamChat()` generator (lines 13–46).
  No changes required here — metadata events already pass through.
- `backend/app/agents/prompts/router_prompt.py` — router few-shot examples.
  Verify that "Tôi muốn điền tờ khai thường trú" with a prior uploaded
  image produces `execution_plan: ["ocr_fn", "form_filler_fn"]`. If no
  matching example exists, add one.

### Outputs

1. `backend/app/agents/nodes/synthesizer.py` — when `mode == "form_fill_complete"`,
   include `filled_form_path: state.get("filled_form_path") or ""` in the
   `response_metadata` dict returned by `synthesizer_node`.
2. `backend/app/api/v1/documents.py` — new endpoint `GET /download` (query
   param `path: str`). Calls `StorageService.download(path)`, returns the
   file as `Response(content=bytes, media_type="application/pdf")` with
   `Content-Disposition: attachment; filename="to-khai.pdf"` header.
   Rate-limited at `5/minute` (reuse `UPLOAD_RATE_LIMIT`).
3. `frontend/src/components/chat/ChatWidget.tsx` — in the `metadata` event
   handler (currently line 87), add a branch: if
   `parsed.metadata?.filled_form_path`, call `updateMessage(assistantId,
   { filledFormPath: parsed.metadata.filled_form_path })`. Add `filledFormPath`
   to the message type. In the message render loop, when a message has
   `filledFormPath` set, render a download button below the bubble:
   `<a href="{BASE}/api/v1/documents/download?path={encodeURIComponent(filledFormPath)}"
   download="to-khai.pdf">📄 Tải xuống tờ khai đã điền</a>` styled with
   the `#CE7A58` brand colour.
4. `backend/app/agents/prompts/router_prompt.py` — verify or add a few-shot
   example where the user references form filling after an CCCD upload, to
   ensure the router consistently emits `["ocr_fn", "form_filler_fn"]`.

### Definition of Done

- [ ] Uploading a CCCD image, then sending "Tôi muốn điền tờ khai thường
      trú" produces `execution_plan: ["ocr_fn", "form_filler_fn"]` (verified
      via backend logs or test)
- [ ] `synthesizer_node` returns `filled_form_path` in `response_metadata`
      when `mode == "form_fill_complete"` (verified by unit test or
      direct state inspection)
- [ ] `GET /api/v1/documents/download?path=...` returns the PDF file bytes
      with correct Content-Type and Content-Disposition headers
- [ ] Download button appears in `ChatWidget.tsx` below the assistant message
      bubble when `response_metadata.filled_form_path` is present in the SSE
      metadata event
- [ ] Clicking the download button retrieves the actual filled PDF
- [ ] Partial fill scenario: when `unfilled_required_fields` is non-empty,
      the synthesizer asks the user for the missing fields by Vietnamese name
      (e.g. "Địa chỉ nơi thường trú mới") — verified by an existing or new
      unit test for `form_fill_partial` mode

### Notes / Constraints

- The download endpoint must validate that the `path` parameter begins with
  `tmp/` or a known MinIO prefix — do not allow arbitrary MinIO path
  traversal. A simple `if not path.startswith(("tmp/", "forms/"))` guard
  is sufficient.
- `StorageService.download()` is synchronous under the hood. It is already
  wrapped in `run_in_executor` internally — do not add another layer.
- Adding `filledFormPath` to the `Message` type in `chatStore.ts` is
  required. The `Message` interface lives in `frontend/src/lib/types/index.ts`
  or inline in the store — locate it before editing `ChatWidget.tsx`.
- The `forms.py` stub `GET /filled/{file_path}` raises `NotImplementedError`.
  Either implement it there or add the download route to `documents.py` and
  remove the stub. Do not leave both.

---

## TASK-APP-03: Basic authentication gate

**Priority:** High

### Goal

The portal currently has no authentication. Any person who opens
`localhost:3000` has full access. For a demo evaluation and project report
demonstration, a minimal access gate is required to prevent accidental
access during evaluation and to satisfy the "access control" non-functional
requirement in the project requirements document.

Implementation: a simple PIN-based gate on the frontend only.
No backend changes required. No JWT, no user accounts, no server-side
validation — this is a demo gate, not production security.

### Inputs

- `frontend/src/app/` — Next.js App Router root. The gate must apply to all
  routes. The best placement is either a root `layout.tsx` client-side check
  or a Next.js middleware file (`frontend/src/middleware.ts`).
- `frontend/src/app/layout.tsx` (or root layout) — the wrapping component
  where the PIN gate can be inserted as a conditional render before
  `{children}`.
- No backend files are modified.

### Outputs

1. `frontend/src/components/auth/PinGate.tsx` (new file) — a full-screen
   overlay component that:
   - Renders the portal logo, a single PIN input field, and a "Xác nhận"
     button.
   - On mount, checks `localStorage.getItem("dvc_authenticated")`. If `"true"`,
     renders `null` immediately (gate is transparent).
   - On submit, hashes the entered PIN (or compares to `process.env.NEXT_PUBLIC_ACCESS_PIN`
     directly, since client-side hashing is security theatre here) and if
     correct, calls `localStorage.setItem("dvc_authenticated", "true")` and
     sets local state `authenticated = true`.
   - On wrong PIN, displays the error message
     `"Mã PIN không đúng. Vui lòng thử lại."` below the input.
   - Default PIN: `"2026"` (when `NEXT_PUBLIC_ACCESS_PIN` is not set).
2. `frontend/src/app/layout.tsx` — import and render `<PinGate>` wrapping
   `{children}`. The gate is client-only; use `'use client'` boundary
   correctly (the root layout itself cannot be a client component in
   App Router — wrap `<PinGate>` inside a client boundary component or
   render it as a client component sibling to `{children}`).
3. `frontend/.env.local.example` — add `NEXT_PUBLIC_ACCESS_PIN=2026` with
   a comment explaining the purpose.
4. Header component (wherever the global site header renders) — add a
   "Đăng xuất" button that calls
   `localStorage.removeItem("dvc_authenticated")` and `window.location.reload()`.
   Locate the correct header file before editing.

### Definition of Done

- [ ] Visiting `localhost:3000` without prior authentication shows the PIN
      entry screen, not the portal home page
- [ ] Entering the correct PIN grants access and the portal loads normally
- [ ] Refreshing the page after correct PIN entry does not show the gate
      again (persisted in `localStorage`)
- [ ] Entering a wrong PIN shows the Vietnamese error message
      "Mã PIN không đúng. Vui lòng thử lại." without redirecting or
      reloading the page
- [ ] PIN is configurable via `NEXT_PUBLIC_ACCESS_PIN` environment variable
- [ ] A "Đăng xuất" button in the site header clears authentication and
      returns to the PIN screen on next visit (or immediately on click)
- [ ] PIN gate does not break SSR — `localStorage` access is guarded by
      `typeof window !== "undefined"` check

### Notes / Constraints

- `localStorage` is not available during server-side rendering. The
  `PinGate` component must be `'use client'` and must defer the
  `localStorage.getItem` check to `useEffect` (not top-level component body)
  to avoid hydration mismatch.
- The PIN is stored in a `NEXT_PUBLIC_` env var — it is visible in the
  client bundle. This is intentional and acceptable for a demo gate.
- Do not implement a session cookie or HTTP-only token. This task is
  explicitly frontend-only.
- Use `#CE7A58` (portal brand color) for the PIN page button and focus
  ring to maintain visual consistency with the rest of the portal.

---

## TASK-APP-04: Fix SSE streaming speed

**Priority:** Medium

### Goal

The current word-by-word streaming at 20 ms delay (line 171 in `chat.py`:
`await asyncio.sleep(0.02)`) feels slow for short responses and produces
a staccato rhythm for longer Vietnamese sentences. Streaming in character
groups of 3–4 characters at 8 ms intervals gives a more natural typewriter
effect and completes short responses faster.

Additionally, the current SSE generator splits `final_response` on spaces
(`final_response.split(" ")`), which means Vietnamese text without spaces
(e.g., citations, punctuation immediately following a word) can produce
awkward pauses mid-sentence. Switching to character-group emission is
cleaner.

### Inputs

- `backend/app/api/v1/chat.py` — `generate()` SSE generator (lines 166–174).
  Current implementation: `words = final_response.split(" ")`, loop with
  `asyncio.sleep(0.02)`. Metadata event sent after all words.
- `frontend/src/components/chat/ChatWidget.tsx` — `handleSend` accumulates
  chunks into `accumulated` string (lines 80–94). The `updateMessage` call
  re-renders on every chunk — verify that character-level chunks do not
  cause perceptible flicker on Vietnamese diacritics.

### Outputs

1. `backend/app/api/v1/chat.py` — rewrite the `generate()` function:
   - Split `final_response` into groups of 3 characters:
     `chunks = [final_response[i:i+3] for i in range(0, len(final_response), 3)]`
   - `await asyncio.sleep(0.008)` between each chunk (8 ms)
   - Send the metadata event immediately after the last content chunk,
     before `[DONE]` (already correct in current code — preserve this order)
2. `frontend/src/components/chat/ChatWidget.tsx` — no structural changes
   required. Verify that accumulating character-level chunks (`accumulated +=
   parsed.content`) does not produce broken diacritics. Vietnamese characters
   are multi-byte in UTF-8 but single Unicode code points — splitting at the
   Python string level (not byte level) is safe. Add a comment confirming this.

### Definition of Done

- [ ] Short responses (under 50 words) complete streaming in under 2 seconds
      from the time the first chunk arrives
- [ ] Vietnamese diacritics (ữ, ề, ồ, ắ, etc.) render correctly during
      streaming — no broken or placeholder characters visible mid-stream
- [ ] Metadata event (`{"metadata": {...}}`) arrives in the SSE stream
      before `[DONE]` (existing behaviour — must not regress)
- [ ] No visible word-splitting artifacts in the rendered chat bubble text
- [ ] A named unit test `test_generate_streams_char_groups` in
      `tests/unit/test_chat_endpoint.py` verifies that each SSE content
      event contains at most 3 characters and that the sleep value is 0.008

### Notes / Constraints

- Python `str` slicing is by Unicode code point, not byte. Vietnamese
  characters are single code points (e.g., `"ữ"` is U+1EEF, one code point).
  Splitting into 3-character groups is safe and will not break diacritics.
- If the response contains an odd number of characters, the last group will
  have fewer than 3 characters — handle this naturally with the slice syntax.
- Do not change the overall SSE format: `data: {"content": "..."}\n\n` for
  content chunks and `data: {"metadata": {...}}\n\n` for the metadata event.
  The `ChatWidget.tsx` parser relies on the `"content" in parsed` check.
- Changing the sleep value does not require any test changes in
  `test_rate_limiting.py` since those tests mock the entire `generate()`
  coroutine.

---

## TASK-APP-05: UI error messages

**Priority:** High

### Goal

When the backend fails (rate limit, Qdrant unreachable, LLM timeout, invalid
file), the frontend currently shows generic messages or nothing at all:

- `ChatWidget.tsx` catch block (line 96–100): always shows
  `"Xin lỗi, đã có lỗi khi kết nối đến máy chủ. Vui lòng thử lại."` — no
  distinction between a 429 and a 500.
- `ChatWidget.tsx` metadata handler (lines 87–89): reads `metadata.citations`
  but never reads `metadata.mode` — error and fallback modes from the
  synthesizer are silently ignored.
- Procedure form pages: `submitError` state exists but only a generic
  `"Không thể lưu hồ sơ"` message is set on failure.
- Document upload card on procedure pages: `ocrStatus === 'error'` always
  shows `"Không thể đọc thông tin. Vui lòng thử lại."` — no distinction
  between a partial OCR result (HTTP 200, `status="partial"`) and an upload
  validation failure (HTTP 422).

### Inputs

- `frontend/src/components/chat/ChatWidget.tsx` — `handleSend` try/catch
  (lines 79–104). `for await` loop processes SSE chunks. The `fetch` call
  is in `streamChat()` in `client.ts` — HTTP status is checked at line 26
  of `client.ts` and throws `new Error("Chat stream failed")` without
  including the status code.
- `frontend/src/lib/api/client.ts` — `streamChat()` and `apiFetch()`.
  `apiFetch` throws `new Error(\`API ${path} → ${res.status}\`)` — the
  status code is embedded in the error message string. `streamChat()` throws
  `new Error("Chat stream failed")` without the status code.
- `frontend/src/app/thu-tuc/dang-ky-thuong-tru/page.tsx` — `handleOcrUpload`
  (lines 34–80) and form submit handler. Both catch blocks show the same
  generic Vietnamese message.
- `frontend/src/app/thu-tuc/dang-ky-tam-tru/page.tsx` — same pattern.
- `frontend/src/app/thu-tuc/xac-nhan-cu-tru/page.tsx` — same pattern.

### Outputs

1. `frontend/src/lib/api/client.ts` — update `streamChat()` to include the
   HTTP status code in its thrown error:
   `throw new Error(\`STREAM_${res.status}\`)` so callers can distinguish
   429 from 500.
2. `frontend/src/components/chat/ChatWidget.tsx` — update the catch block
   in `handleSend` to parse the error message for a status code:
   - If error message contains `"429"` or `"STREAM_429"` → show
     `"Hệ thống đang bận, vui lòng thử lại sau 30 giây."`
   - If error message contains `"500"` or `"STREAM_500"` → show
     `"Đã xảy ra lỗi hệ thống. Vui lòng thử lại."`
   - Default (network error, unknown) → show existing generic message.
   Also update the metadata event handler to check `parsed.metadata?.mode`:
   - If `mode === "error"` and the errors list (if surfaced in metadata)
     contains `"Không tìm thấy văn bản pháp lý"` → set the assistant message
     content to `"Không tìm thấy thông tin pháp lý phù hợp. Hãy thử đặt
     câu hỏi cụ thể hơn."`
   - If `mode === "fallback"` → show
     `"Tôi chưa hiểu rõ yêu cầu của bạn. Bạn có thể mô tả thêm không?"`
3. `frontend/src/app/thu-tuc/dang-ky-thuong-tru/page.tsx` (and the other
   two procedure pages) — `handleOcrUpload`:
   - If `result.status === "partial"` → show `"Không đọc được thông tin
     đầy đủ từ ảnh. Vui lòng chụp ảnh rõ hơn và thử lại."`
   - If the `api.documents.upload` call throws and the error message contains
     `"422"` → show `"File không hợp lệ. Chỉ chấp nhận ảnh JPG, PNG, WebP
     dưới 5MB."`
   - For form submission failures: if the `api.forms.submit` call throws and
     the error message contains `"422"` → show `"Vui lòng điền đầy đủ thông
     tin bắt buộc trước khi nộp."`; if `"500"` → show `"Không thể nộp hồ
     sơ. Vui lòng thử lại sau."`

### Definition of Done

- [ ] HTTP 429 on chat produces `"Hệ thống đang bận, vui lòng thử lại
      sau 30 giây."` in the assistant bubble
- [ ] HTTP 500 on chat produces `"Đã xảy ra lỗi hệ thống. Vui lòng thử lại."`
- [ ] Empty RAG result (synthesizer `mode=error`) shows
      `"Không tìm thấy thông tin pháp lý phù hợp. Hãy thử đặt câu hỏi
      cụ thể hơn."` in the assistant bubble
- [ ] Document upload with `status="partial"` shows the partial-specific
      Vietnamese guidance message on all three procedure pages
- [ ] HTTP 422 on document upload shows the file-invalid message
- [ ] Form submission failure shows an actionable Vietnamese inline error
      below the submit button
- [ ] No raw English error string (`"API /api/v1/chat → 429"`,
      `"Chat stream failed"`, etc.) is visible to the user at any point

### Notes / Constraints

- The synthesizer `response_metadata` currently contains `mode` but does
  not surface the `errors` list to the client. Adding `errors` to
  `response_metadata` (in `synthesizer_node`) is needed to distinguish
  specific error types in the frontend. Keep the errors list short — only
  the first error string, truncated to 120 characters, to avoid exposing
  internal stack traces.
- The `metadata` SSE event in `ChatWidget.tsx` is currently only used to
  extract citations. The metadata handler should be expanded but must remain
  backwards-compatible: if `metadata.citations` is absent, no crash.
- The three procedure pages have nearly identical error handling patterns —
  consider extracting a shared `handleUploadError(result, setOcrStatus,
  setOcrMessage)` utility function to avoid repeating the same conditional
  three times. This is a judgment call; do not over-abstract if it adds
  complexity.

---

## TASK-APP-06: Loading indicators on procedure pages

**Priority:** Medium

### Goal

The three residence procedure pages have incomplete loading states:

- The OCR upload card has `ocrStatus` state and shows "Đang đọc thông tin
  CCCD..." during upload — this is already partially implemented in the
  `thuong-tru` page. Verify it is consistent across all three pages.
- The **form submit button** has no loading indicator. When the user clicks
  "Nộp hồ sơ", the button does nothing visible for 1–3 seconds while the
  `POST /api/v1/forms/submit` call runs. During this time the user may click
  again (double submission risk) and there is no feedback.
- After successful submission, the tracking code is currently shown in an
  alert or `submitError` state — it should be displayed prominently in a
  success banner with the tracking code visible.

### Inputs

- `frontend/src/app/thu-tuc/dang-ky-thuong-tru/page.tsx` — form submit
  handler (look for the `onSubmit` function passed to `useForm`). Currently
  uses `submitError` state (line 27) but no `isSubmitting` state. The
  `<button type="submit">` does not have a disabled or spinner state.
- `frontend/src/app/thu-tuc/dang-ky-tam-tru/page.tsx` — same pattern.
- `frontend/src/app/thu-tuc/xac-nhan-cu-tru/page.tsx` — same pattern.
- `frontend/src/lib/api/client.ts` — `api.forms.submit()` returns
  `{ ma_ho_so, form_type, submitted_at, status, message }`.

### Outputs

For each of the three procedure pages (`dang-ky-thuong-tru/page.tsx`,
`dang-ky-tam-tru/page.tsx`, `xac-nhan-cu-tru/page.tsx`):

1. Add `const [isSubmitting, setIsSubmitting] = useState(false)` and
   `const [submittedCode, setSubmittedCode] = useState<string | null>(null)`.
2. In the `onSubmit` handler: call `setIsSubmitting(true)` before the API
   call and `setIsSubmitting(false)` in the `finally` block. On success,
   call `setSubmittedCode(result.ma_ho_so)`.
3. The submit button: when `isSubmitting` is true, render a spinner SVG
   (or Tailwind `animate-spin` circle) and the text `"Đang nộp hồ sơ…"`.
   Set `disabled={isSubmitting || !!submittedCode}`.
4. When `submittedCode` is not null, render a success banner **above the
   form** (or replace the form entirely) with:
   - Green checkmark icon (use `lucide-react Check` or a Unicode ✓)
   - Message: `"Hồ sơ đã được tiếp nhận thành công."`
   - Tracking code displayed prominently: `"Mã hồ sơ của bạn: {submittedCode}"`
     in a monospace font or styled box
   - A "Nộp hồ sơ khác" button that clears `submittedCode` and resets the
     form via `reset()` from `useForm`
5. The OCR upload card spinner text `"Đang đọc thông tin CCCD…"` must be
   present and consistent across all three pages. If any page is missing it,
   add it.

All new text and loading states must use the `#CE7A58` brand colour for
spinners and accents.

### Definition of Done

- [ ] Submit button shows spinner and "Đang nộp hồ sơ…" text and is
      disabled during the `POST /api/v1/forms/submit` API call on all three
      procedure pages
- [ ] Double-click on submit during submission does not trigger a second
      API call (button is disabled)
- [ ] Tracking code (`ma_ho_so`) is displayed prominently in a success
      state after submission on all three pages
- [ ] "Nộp hồ sơ khác" button resets the form and clears the success state
- [ ] OCR upload shows `"Đang đọc thông tin CCCD…"` during the upload
      request on all three pages
- [ ] All loading states use `#CE7A58` brand colour for spinners and
      accents, consistent with the rest of the portal UI
- [ ] Loading states clear correctly on both success and error

### Notes / Constraints

- React Hook Form's `formState.isSubmitting` is an alternative to a manual
  `isSubmitting` state — it is automatically `true` during an async `onSubmit`
  handler. Use this if the form submit is handled directly by `handleSubmit`;
  use manual state if the submit triggers a separate async function outside
  the form context.
- The three pages have very similar structure. Make the same changes to all
  three to ensure consistency. Do not implement a pattern on one page and
  leave the others as-is.
- The `animate-spin` Tailwind utility is available in the project. Use a
  simple `<svg className="animate-spin w-4 h-4 inline mr-1" ...>` for the
  spinner rather than a third-party component.

---

## TASK-APP-07: Citation bolding in chat responses

**Priority:** Medium

### Goal

Legal citations in the form `[Điều X, Nghị định YYY/YYYY/NĐ-CP]` and
`[Điều X, Luật YYY YYYY]` currently render as plain text inside the
assistant message bubble in `ChatWidget.tsx`. A demo evaluator looking at
chat responses cannot immediately identify legal source references — they
blend with the surrounding prose.

Making citations visually distinct (bold, coloured) immediately signals that
the system is grounding its answers in specific legal texts, which is the
core scientific claim of the project.

`[unverified: ...]` patterns (produced by `verify_citations()` in
`citation_formatter.py` when a cited article was not in the retrieved chunks)
must render differently — grey italic — to signal reduced confidence.

This is a pure frontend change. No backend modifications required.

### Inputs

- `frontend/src/components/chat/ChatWidget.tsx` — the message render loop
  (lines 180–203). Currently renders content as:
  `<span className="whitespace-pre-wrap">{msg.content}</span>`. This must
  be replaced with a component that parses and highlights citations.
- `frontend/src/lib/types/index.ts` (or wherever `Citation` type is defined)
  — no changes needed but read first to understand the existing data model.

### Outputs

1. `frontend/src/components/chat/ChatWidget.tsx` — replace the plain
   `<span>{msg.content}</span>` with a `<FormattedMessage content={msg.content} />`
   component defined in the same file (or extracted to a new file if it
   becomes complex). `FormattedMessage` splits the content string by the
   citation pattern, then renders:
   - Normal text segments: plain `<span>`
   - Verified citation matches `[Điều \d+[a-z]?, [^\]]+]`:
     `<span className="font-bold text-[#CE7A58] text-xs">[Điều X, ...]</span>`
     (or a slightly muted variant like `text-[#B8694A]` for legibility)
   - Unverified citation matches `[unverified: [^\]]+]`:
     `<span className="text-[#999] italic text-xs">[unverified: ...]</span>`
   The splitting must use `String.prototype.split()` with a capturing regex
   so that citation spans are preserved as array elements.
2. Apply the same rendering logic during streaming — as `accumulated` grows
   character-by-character (after TASK-APP-04), the `FormattedMessage`
   component must re-render without flicker. Since incomplete citation
   brackets will be rendered as plain text until the closing `]` arrives,
   this is naturally handled by the regex not matching partial patterns.

### Definition of Done

- [ ] Citations in the format `[Điều X, Nghị định YYY/YYYY/NĐ-CP]` render
      as bold coloured text visually distinct from surrounding prose
- [ ] Citations in the format `[Điều X, Luật YYY YYYY]` are also matched
      and styled (the regex must handle both Nghị định and Luật formats)
- [ ] `[unverified: ...]` citations render in grey italic, distinct from
      verified citations
- [ ] Non-citation text is unaffected — no rendering artifacts on prose
      paragraphs, numbered lists, or punctuation
- [ ] The component works correctly during streaming (partial citation
      text before the closing `]` renders as plain text, not broken markup)
- [ ] No new dependencies introduced — the implementation uses only React
      and regex, no third-party markdown parser
- [ ] A manual smoke test: send a RAG query that produces a citation, verify
      the styling in the browser

### Notes / Constraints

- The `dangerouslySetInnerHTML` approach must NOT be used — use React
  element arrays (`.map()` over split segments) to avoid XSS risk.
- The citation regex must be non-greedy on the inner content to avoid
  matching across two citations:
  `\[Điều \d+[a-z]?,\s[^\]]+\]` is sufficient.
- The `[unverified: ...]` pattern produced by `verify_citations()` always
  has the exact prefix `[unverified: ` — match this literally, not as a
  general bracket pattern.
- For streaming: since `FormattedMessage` is a pure functional component
  that takes `content: string` as a prop and recomputes the split on every
  render, performance is acceptable for responses under 2 000 characters.
  No memoisation required at this stage.

---

## TASK-APP-08: Use case documentation

**Priority:** High

### Goal

Create `docs/USE_CASES.md` with three formal use cases in standard
structured format. These are required by the project requirements document
(section 2.1 — Use case cụ thể). Each use case must cover a distinct
core feature of the system and include enough detail for a project evaluator
to understand what the system does and why each component exists.

The three use cases map to the three major features of the pipeline:
- RAG-based legal Q&A
- OCR-driven form pre-fill
- DAG-based procedural dependency resolution

### Inputs

Read before writing:
- `docs/PROJECT_CONTEXT.md` §1 (System Vision, Current Scope) and §2.2
  (Multi-Agent Pipeline) — for accurate pipeline component names
- `backend/app/agents/nodes/rag.py` — for accurate RAG pipeline description
- `backend/app/agents/nodes/synthesizer.py` — for response mode descriptions
- `backend/app/core/procedure_graph.py` — for DAG resolution description
- `backend/ingestion/ingest_procedures.py` — for actual procedure IDs and
  dependency edges to reference in UC-003

### Outputs

`docs/USE_CASES.md` (new file) containing:

**UC-001: Tra cứu thông tin pháp lý thủ tục hành chính**
- Actor: Công dân có nhu cầu tìm hiểu thủ tục hành chính
- Preconditions: Legal documents for the queried domain have been ingested
  into Qdrant; the backend and all Docker services are running
- Main flow (numbered steps):
  1. Citizen sends a Vietnamese question about a residence procedure via
     the chat widget
  2. `router_node` parses the message, emits `execution_plan: ["rag_fn"]`
     and sets `target_procedure_id` if a procedure is mentioned
  3. `enrichment_node` checks two-condition guard — `form_filler_fn` is not
     in plan, so returns `{}` immediately (no DAG enrichment)
  4. `plan_executor_node` calls `rag_fn` via `NODE_REGISTRY`
  5. `rag_fn` builds scope list from `filing_jurisdiction`, cascades through
     Qdrant with hybrid dense+BM25 search, merges with RRF, applies 6 000-
     token budget
  6. LLM generates a cited Vietnamese answer; `verify_citations()` flags any
     unverified references
  7. `synthesizer_node` detects `mode=rag_only`, returns `final_response`
     directly (RAG LLM-skip optimisation — no second LLM call)
  8. Chat endpoint streams the answer word-by-word via SSE; the frontend
     renders citation chips below the bubble
- Alternative flows:
  - A-1 (No matching chunks): all scope levels return zero chunks above
    `RAG_MIN_SCORE_THRESHOLD` → `rag_fn` returns error, `synthesizer_node`
    enters `mode=error` → response is `"Không tìm thấy thông tin pháp lý
    phù hợp."`
  - A-2 (Jurisdiction fallback): chunk found at national scope (VN) but
    not at ward scope (VN-HCM-26968) → `scope_notice_included=True` →
    `synthesizer_node` calls LLM to weave in scope fallback notice
- Postconditions: Citizen receives a cited Vietnamese answer; conversation
  history updated in Redis; no session data mutated (RAG is read-only)
- System components: Router → rag_fn → Synthesizer
- Text flow diagram included

**UC-002: Đọc thông tin từ CCCD và điền tờ khai tự động**
- Actor: Công dân cần nộp hồ sơ thủ tục cư trú (Đăng ký thường trú
  TTHC-001)
- Preconditions: CCCD image available (QR-encoded or legible scan);
  `TTHC-001.pdf` AcroForm template in MinIO; backend running
- Main flow (8 numbered steps) covering image upload → QR decode attempt →
  OCR fallback → `PersonalData` session persistence → form fill request →
  `execution_plan: ["ocr_fn", "form_filler_fn"]` → PDF filled → download
  link returned
- Alternative flows:
  - A-1 (QR decode succeeds, confidence=1.0): PaddleOCR is skipped entirely
  - A-2 (Partial fill — missing fields): `unfilled_required_fields` non-empty
    → `synthesizer_node` enters `mode=form_fill_partial` → system asks
    citizen for missing fields by Vietnamese name
- Postconditions: Filled PDF available in MinIO `tmp/`; download link
  surfaced in chat
- System components: Upload endpoint → OCRService → Redis → Router →
  enrichment_node → plan_executor → ocr_fn + form_filler_fn → Synthesizer

**UC-003: Tra cứu thứ tự thực hiện thủ tục phụ thuộc**
- Actor: Công dân chưa biết cần thực hiện thủ tục gì trước
- Preconditions: `procedure_dependencies` table seeded with housing DAG
  edges (TTHC-003 → TTHC-001 mandatory, TTHC-003 → TTHC-002 conditional);
  RAG corpus ingested
- Main flow: citizen asks about TTHC-003 → Router sets `target_procedure_id`
  and `form_filler_fn` in plan → `enrichment_node` calls `procedure_planner_fn`
  (two-condition guard passes) → topological sort resolves [TTHC-001,
  TTHC-002, TTHC-003] in dependency order → `synthesizer_node` explains
  required order with legal citations
- Alternative flows:
  - A-1 (All prerequisites complete): `procedure_planner_fn` finds all
    deps in `completed_procedures` → plan proceeds directly to TTHC-003
  - A-2 (Out of scope procedure ID): `procedure_planner_fn` returns error
    → system responds with Vietnamese out-of-scope message
- Postconditions: Citizen understands the required sequence and its legal
  basis
- System components: Router → enrichment_node → procedure_planner_fn →
  plan_executor → rag_fn → Synthesizer

### Definition of Done

- [ ] `docs/USE_CASES.md` created with all three use cases
- [ ] Each use case has all required sections: ID, Name, Actor,
      Preconditions, Main flow (numbered), Alternative flows (≥2 each),
      Postconditions, Related procedures/components
- [ ] Alternative flows cover at least 2 error or edge-case scenarios each
- [ ] A text-based flow diagram (ASCII box-and-arrow) is present for
      each use case showing the system components involved
- [ ] Vietnamese terminology used throughout for citizen-facing concepts
      (thủ tục, công dân, tờ khai, hồ sơ, etc.)
- [ ] Component names match implementation exactly: `router_node`,
      `enrichment_node`, `plan_executor_node`, `rag_fn`, `ocr_fn`,
      `form_filler_fn`, `synthesizer_node` — not aliases or descriptions

### Notes / Constraints

- The three DAG edges to reference in UC-003 are: TTHC-003 → TTHC-001
  (mandatory), TTHC-003 → TTHC-002 (conditional), plus the multi-domain
  edges TTHC-CR-002 → TTHC-CR-001 and TTHC-AD-002 → TTHC-AD-001. UC-003
  should focus on the housing domain (TTHC-001/002/003) since that is the
  runnable demo domain.
- Do not invent feature behaviour that does not exist. If the download
  link (TASK-APP-02) is not yet implemented, UC-002 should note it as
  "step N: download link surfaced [pending TASK-APP-02]" rather than
  describing a feature that does not work.

---

## TASK-APP-09: API documentation

**Priority:** High

### Goal

Create `docs/API.md` documenting all functional API endpoints with enough
detail for a project evaluator and for the project report API specification
section. FastAPI auto-generates OpenAPI at `/docs` but the auto-generated
spec is not human-readable narrative documentation and cannot be submitted
as part of the written report.

### Inputs

Read these files before writing, in full:
- `backend/app/api/v1/chat.py` — full SSE format, session hydration, error
  responses
- `backend/app/api/v1/documents.py` — upload endpoint, response schema,
  rate limits
- `backend/app/api/v1/forms.py` — `POST /submit` implementation, response
  schema, tracking code format
- `backend/app/schemas/chat.py` — `ChatRequest`, `ChatResponse`, `Citation`
- `backend/app/schemas/document.py` — `DocumentUploadResponse`
- `backend/app/schemas/form.py` — `FormSubmissionRequest`,
  `FormSubmissionResponse`
- `backend/app/config.py` — `CHAT_RATE_LIMIT`, `UPLOAD_RATE_LIMIT` values

### Outputs

`docs/API.md` (new file) covering the following endpoints in full:

**1. POST /api/v1/chat**
- Base URL, authentication (session_id-based, no JWT)
- Request body: `ChatRequest` schema with field types, constraints, examples
  - `session_id: str` — UUID or arbitrary string, required
  - `message: str` — user's Vietnamese message, required, max length note
  - `image_path: str | None` — optional MinIO path from prior upload
- Response: `text/event-stream` SSE format
  - Content chunks: `data: {"content": "..."}\n\n` — each chunk is ≤3
    characters (after TASK-APP-04) or 1 word (current implementation)
  - Metadata event: `data: {"metadata": {"mode": "...", "scope_used": "...",
    "scope_notice_included": bool, "rag_confidence": "high"|"medium"|"low"|null,
    "filled_form_path": "..."|null}}\n\n`
  - Termination: `data: [DONE]\n\n`
  - Mode values: `"rag_only"`, `"form_fill_complete"`, `"form_fill_partial"`,
    `"error"`, `"circuit_breaker"`, `"fallback"`
- Error responses: 422 (invalid request body), 429 (rate limit exceeded —
  10 req/min per session_id), 500 (GraphRecursionError)
- Rate limit: `CHAT_RATE_LIMIT` (default: `10/minute`, keyed by `session_id`)
- Example request (JSON body) and example SSE stream output (5–6 events)

**2. POST /api/v1/documents/upload**
- Request: `multipart/form-data`
  - `file: UploadFile` — MIME whitelist: `image/jpeg`, `image/png`,
    `image/webp`, `application/pdf`; max size: 5 MB
  - `session_id: str` — links the document to an active session
- Response: `DocumentUploadResponse` JSON
  - `status: "success" | "partial"` — `"success"` means OCR succeeded;
    `"partial"` means file stored but OCR failed
  - `tmp_path: str` — MinIO object path, e.g. `tmp/{session_id}/{uuid}.jpg`
  - `personal_data: PersonalData | null` — extracted personal data or null
    on partial success
  - `ocr_confidence: float` — mean field confidence (0.0–1.0); 1.0 for
    QR-decoded documents
  - `message: str` — Vietnamese success or guidance message
- Error responses: 422 (empty file, invalid MIME, file too large),
  500 (MinIO storage failure)
- Rate limit: `UPLOAD_RATE_LIMIT` (default: `5/minute`, keyed by `session_id`)
- QR-first pipeline note: QR decode is attempted before PaddleOCR; on
  QR success, `ocr_confidence=1.0` and PaddleOCR is skipped

**3. POST /api/v1/forms/submit**
- Request: `FormSubmissionRequest` JSON
  - `form_type: "thuong-tru" | "tam-tru" | "xac-nhan"` — procedure identifier
  - `session_id: str`
  - `submission_mode: "manual" | "ai"` — `"ai"` reserved for form_filler_fn
  - `form_data: ResidenceFormData` — all required form fields; must not be
    entirely empty (422 if all fields null)
- Response: `FormSubmissionResponse` JSON
  - `ma_ho_so: str` — tracking code, format: `DVC-{YYYYMMDD}-{6 chars}`,
    e.g. `DVC-20260413-K7FX3P`
  - `form_type: str`
  - `submitted_at: datetime (ISO 8601 UTC)`
  - `status: "received"`
  - `message: str` — Vietnamese confirmation with tracking code
- Error responses: 422 (empty `form_data`), 500 (DB write failure)
- No rate limit currently configured on this endpoint

**4. GET /api/v1/documents/download** (pending TASK-APP-02)
- Query params: `path: str` — MinIO object path from `tmp/` or `forms/`
  prefix
- Response: PDF binary with `Content-Type: application/pdf` and
  `Content-Disposition: attachment; filename="to-khai.pdf"`
- Error responses: 400 (invalid path prefix), 404 (object not found in
  MinIO), 500 (download failure)
- Note: this endpoint is not yet implemented; see TASK-APP-02

### Definition of Done

- [ ] `docs/API.md` created covering all 4 endpoints (endpoint 4 marked as
      "pending TASK-APP-02" if not yet implemented)
- [ ] Each endpoint documents: HTTP method + path, description, request
      schema (field names, types, constraints), response schema, all error
      codes, example request, example response
- [ ] SSE stream format documented with a complete 5–6 event example showing
      content chunks, metadata event, and `[DONE]`
- [ ] All response mode values documented for the chat endpoint
- [ ] Rate limits documented with default values and keying strategy
- [ ] `PersonalData` schema fields listed with Vietnamese descriptions for
      non-obvious fields (e.g. `full_name_latin`, `field_confidences`)
- [ ] Consistent Markdown formatting throughout (headers, code blocks,
      tables for schema fields)

### Notes / Constraints

- Do not simply copy-paste Pydantic model definitions — translate them into
  a human-readable table with a description column for each field.
- Vietnamese field descriptions should match what a Vietnamese evaluator
  would expect: e.g. `ma_ho_so` → "Mã số hồ sơ hành chính dùng để tra
  cứu trạng thái", not just "tracking code".
- The `PersonalData` schema has many fields — focus on the fields actually
  populated by the OCR pipeline (full_name, date_of_birth, gender, id_number,
  permanent_address, extraction_confidence, field_confidences).

---

## TASK-APP-10: Performance baseline measurement

**Priority:** Medium

### Goal

Run and document timing measurements for the key system operations. This is
required for the Performance non-functional requirement in the project report.
Without measured numbers, the performance claims in the report are
unsubstantiated.

The measurements must capture: time-to-first-token (TTFT) for chat responses
and total OCR upload processing time. Both are affected by cold-start behaviour
and must be documented with constraints noted.

### Inputs

- `backend/app/api/v1/chat.py` — endpoint to benchmark
- `backend/app/api/v1/documents.py` — upload endpoint to benchmark
- `backend/data/mock_documents/` — synthetic CCCD images to use for
  upload benchmarks; use `category_1_clean_qr/` subdirectory for consistent
  QR-path benchmarks
- No production files are modified by this task

### Outputs

1. `tests/performance/measure_latency.py` (new file) — a standalone Python
   script (no pytest, no app/ imports) that:
   - Accepts `--backend http://localhost:8000` CLI argument (default:
     `http://localhost:8000`)
   - **Chat TTFT benchmark** (10 iterations):
     For each iteration, sends `POST /api/v1/chat` with `session_id=f"perf-{i}"`,
     `message="Tôi cần đăng ký thường trú, cần những giấy tờ gì?"`.
     Measures `t_first_chunk` (time from request send to first `data:` line
     received) and `t_total` (time to `data: [DONE]`).
     Waits 7 seconds between iterations to stay within the 10 req/min rate
     limit (10 iterations at 7 s = 70 s total — within the 1-minute window).
   - **OCR upload benchmark** (5 iterations):
     For each iteration, uploads one image from `backend/data/mock_documents/`
     to `POST /api/v1/documents/upload`. Measures `t_total` (request to
     response JSON). Uses a different `session_id` per iteration.
   - Prints a results table to stdout:
     ```
     Chat TTFT:   min=Xs  max=Xs  mean=Xs  p95=Xs
     Chat Total:  min=Xs  max=Xs  mean=Xs  p95=Xs
     OCR Upload:  min=Xs  max=Xs  mean=Xs  p95=Xs
     ```
   - Uses only `httpx` (sync) and `statistics` from the standard library —
     no extra dependencies.
2. `tests/performance/PERFORMANCE_RESULTS.md` (new file) — populated with
   real numbers from a run with all Docker services running and the embedding
   model pre-loaded (post TASK-APP-01). Sections:
   - Environment: OS, Python version, embedding backend, LLM backend, CPU
     (since bge-m3 runs on CPU)
   - Measurement table (copy of script output)
   - Known constraints (see Notes below)
   - Interpretation: what the numbers mean for the demo scenario

### Definition of Done

- [ ] `tests/performance/measure_latency.py` is created and runnable with
      `python tests/performance/measure_latency.py --backend http://localhost:8000`
- [ ] Script requires no imports beyond `httpx`, `statistics`, `argparse`,
      `time`, `os`, `pathlib`
- [ ] Script measures both TTFT and total response time for chat
- [ ] Script measures total processing time for OCR upload
- [ ] `PERFORMANCE_RESULTS.md` is populated with real numbers from a local
      run (not placeholder text)
- [ ] Known constraints explicitly documented in `PERFORMANCE_RESULTS.md`:
      bge-m3 cold start, Gemini/Claude rate limits, PaddleOCR CPU inference
      time, Windows process overhead
- [ ] Script does not hardcode absolute paths — uses relative paths from the
      script's `__file__` location to find mock CCCD images

### Notes / Constraints

- The benchmark must be run **after** TASK-APP-01 (eager model loading) is
  complete so that cold-start latency does not pollute the TTFT numbers.
  If run before TASK-APP-01, document this explicitly in
  `PERFORMANCE_RESULTS.md` and note which samples included cold-start.
- Gemini free tier: ~5 req/min. With a 7-second inter-request delay, 10
  chat requests will take ~70 seconds minimum. If using Gemini, add a
  `--sleep` parameter (default 7) to allow the user to adjust.
- PaddleOCR CPU inference: ~3–8 seconds per image on typical development
  hardware. This is expected and must be noted in results.
- `httpx` supports streaming responses — use `httpx.stream("POST", ...)` to
  read the SSE stream chunk-by-chunk for accurate TTFT measurement.
- p95 with 10 samples is meaningless statistically — note this in the
  results file. The measurements are indicative, not rigorous.

---

## TASK-APP-11: README.md

**Priority:** Critical

### Goal

Create `README.md` at the repository root. This is explicitly required by
the project requirements document (section 4.2). The README is the first
file an evaluator reads and must enable a developer to install and run the
system from scratch.

There is currently no `README.md` at the repository root (confirmed by git
status and directory listing). The nearest documentation is
`docs/PROJECT_CONTEXT.md` (architecture) and `docs/PROJECT_STATUS.md`
(progress), but neither serves as an installation guide.

### Inputs

Read before writing:
- `docs/PROJECT_CONTEXT.md` §1 (System Vision) and §2.1 (System Layers
  Diagram, ASCII art) — for the architecture overview section
- `docs/PROJECT_STATUS.md` §1.1 (Completed items) — for accurate feature list
- `backend/app/config.py` — for the complete list of environment variables
  and their defaults
- `docker-compose.yml` (project root) — for Docker service names and ports
- `backend/ingestion/ingest_procedures.py` — for the exact command to seed
  procedures
- `backend/ingestion/ingest_legal_docs.py` — for the `--domain` CLI flag syntax
- `backend/alembic/` — for the `alembic upgrade head` command context

### Outputs

`README.md` at repository root (new file) with exactly 8 sections:

**Section 1: Project title and description**
- Vietnamese title: "Hệ thống Trợ lý AI Dịch vụ công"
- English title: "DichVuCong AI Assistant"
- One-paragraph Vietnamese description: what the system does, who it is for
- One-paragraph English description (same content, translated)

**Section 2: System architecture overview**
- Reference the diagram from `PROJECT_CONTEXT.md` §2.1 (reproduce the ASCII
  box diagram or paraphrase it)
- Short table of components: Frontend (Next.js), Backend (FastAPI), AI
  (Claude/Gemini + bge-m3), Vector DB (Qdrant), Storage (MinIO, Redis,
  PostgreSQL)

**Section 3: Prerequisites**
- Docker Desktop (version ≥ 24.0)
- Python 3.12 (with `pyenv` or direct install)
- Node.js 18+ and npm
- Git
- Platform notes: tested on Windows 11 and Ubuntu 22.04

**Section 4: Environment setup**
- How to clone and navigate to the project directory
- How to create `.env` from `.env.example` (note that `.env.example` must
  exist — create it as a side output of this task if it doesn't)
- List of required env vars with descriptions:
  - `ANTHROPIC_API_KEY` or `GOOGLE_API_KEY` (one is required for LLM)
  - `REDIS_PASSWORD` (must match docker-compose.yml)
  - `REDIS_ENCRYPTION_KEY` (32-byte base64, can generate with Python)
  - `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` (default: `minioadmin`)
  - `EMBEDDING_BACKEND` (default: `bge-m3`; set to `openai` if no GPU)
- How to generate `REDIS_ENCRYPTION_KEY`:
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

**Section 5: Running the system**
Step-by-step commands:
```bash
docker compose up -d
cd backend
python -m alembic upgrade head
python ingestion/ingest_procedures.py
python ingestion/ingest_legal_docs.py --domain housing
python -m uvicorn app.main:app --reload --port 8000
# In a new terminal:
cd frontend
npm install
npm run dev
```
Note: verify each service is healthy with `docker compose ps` before
running backend commands.

**Section 6: Running tests**
```bash
cd backend
PYTHONPATH=. .venv/Scripts/pytest tests/unit/ -v          # Windows
PYTHONPATH=. .venv/bin/pytest tests/unit/ -v               # Linux/Mac
# Integration tests (requires Docker services running):
pytest tests/integration/ -m integration
```
Note current test counts: 278 unit tests, 8 integration tests.

**Section 7: Project structure**
Top-level directory tree with one-line descriptions:
```
dichvucong/
├── backend/
│   ├── app/          # FastAPI application (routes, agents, services, schemas)
│   ├── ingestion/    # Offline data preparation scripts
│   ├── data/         # Raw legal PDFs, form templates, mock images
│   ├── tests/        # Unit and integration tests
│   └── alembic/      # Database migration scripts
├── frontend/
│   └── src/
│       ├── app/      # Next.js App Router pages
│       ├── components/ # React UI components (chat widget, forms)
│       └── lib/      # API client, Zustand stores, TypeScript types
├── docs/             # Project documentation
└── docker-compose.yml
```

**Section 8: Known limitations**
- bge-m3 cold start: first embedding request after server start may take
  2–5 minutes if TASK-APP-01 is not applied; server must be fully started
  before sending the first chat message
- Gemini free tier: 5 req/min rate limit constrains sustained throughput;
  Claude Tier 1 removes this constraint
- OCR accuracy: PaddleOCR requires clean, well-lit images; blurry or rotated
  scans will produce low-confidence extractions
- No production hardening: CORS locked to localhost, no TLS, demo PIN auth
  only — not suitable for deployment

### Definition of Done

- [ ] `README.md` exists at the repository root
- [ ] All 8 sections are present with the specified content
- [ ] All commands in sections 5 and 6 are copy-pasteable and correct for
      both Windows and Linux/Mac
- [ ] Both Vietnamese and English project descriptions are present in
      section 1
- [ ] `.env.example` exists at the repository root with all required
      variables (created as a side output if missing)
- [ ] A reviewer with no prior knowledge of the project can follow the
      README alone to get the system running (mental dry-run verified against
      actual project structure)
- [ ] No placeholder text (`[TODO]`, `[INSERT]`) remains in the final file

### Notes / Constraints

- Verify actual command paths before writing. On Windows, the venv is at
  `backend/.venv/Scripts/`. On Linux/Mac it is `backend/.venv/bin/`.
  Document both.
- The `ingest_legal_docs.py --domain housing` command requires the legal
  PDF files to be present in `backend/data/legal_documents/`. Note this
  dependency — the `.doc` files must be converted to PDF first (see
  CLAUDE.md for the LibreOffice conversion command).
- Do not promise features that are not implemented. Section 8 must
  accurately list limitations rather than hiding them.

---

## TASK-APP-12: Installation and User guides

**Priority:** High

### Goal

Create two documents required by the project requirements document:
`docs/INSTALLATION.md` and `docs/USER_GUIDE.md`. The installation guide
enables a technical reviewer to reproduce the running system. The user guide
explains the system to a non-technical Vietnamese citizen evaluator.

### Inputs

Read before writing:
- `README.md` (after TASK-APP-11 is complete — or draft based on known
  project structure if TASK-APP-11 is still in progress)
- `docs/PROJECT_CONTEXT.md` §1 (scope, features) and §2.4 (OCR pipeline)
  — for user guide feature descriptions
- `backend/app/config.py` — for all environment variables
- `docker-compose.yml` — for service health check commands
- `frontend/src/app/thu-tuc/dang-ky-thuong-tru/page.tsx` — for accurate
  description of the form filling UI flow

### Outputs

**1. `docs/INSTALLATION.md`** (new file) — detailed step-by-step for a
fresh Windows 11 machine (primary target) with Linux/Mac notes where
different:

Sections:
- **Prerequisites**: Docker Desktop installation link and minimum version;
  Python 3.12 via python.org; Node.js 18 LTS via nodejs.org; Git
- **Clone repository**: `git clone` command, `cd dichvucong`
- **Environment configuration**: copy `.env.example` to `.env`; fill in each
  required variable with explanation; note which variables have working
  defaults and which require real credentials (API keys)
- **Generate REDIS_ENCRYPTION_KEY**: exact Python one-liner
- **Start Docker services**: `docker compose up -d`; verify with
  `docker compose ps` — all 4 services (postgres, redis, qdrant, minio)
  must show `healthy` or `running`
- **Backend Python setup**: `cd backend`; create venv
  (`python -m venv .venv`); activate (`.\\.venv\\Scripts\\activate` on Windows,
  `source .venv/bin/activate` on Linux); install deps
  (`pip install -r requirements.txt`)
- **Database migrations**: `python -m alembic upgrade head` — expected output:
  `Running upgrade -> 0001_initial_schema ...` etc.
- **Seed procedures**: `python ingestion/ingest_procedures.py` — expected
  output: procedure IDs logged
- **Convert legal documents to PDF**: LibreOffice command for `.doc` → `.pdf`
  conversion (required before ingestion)
- **Ingest legal documents**: `python ingestion/ingest_legal_docs.py
  --domain housing` — note this takes ~10–30 minutes on first run
  (Docling model download ~2 GB)
- **Start backend**: `python -m uvicorn app.main:app --reload --port 8000`;
  verify at `http://localhost:8000/docs`
- **Frontend setup**: `cd ../frontend`; `npm install`; `npm run dev`;
  verify at `http://localhost:3000`
- **Verification test**: send a chat message "Đăng ký thường trú cần
  những giấy tờ gì?" and confirm a cited response is returned

**2. `docs/USER_GUIDE.md`** (new file) — how to use the system as a citizen.
Written primarily in Vietnamese:

Sections:
- **Tổng quan**: three main features (legal Q&A, CCCD upload + form fill,
  procedure lookup); one paragraph each
- **Tính năng 1: Hỏi đáp thủ tục hành chính**: how to open the chat
  widget; what types of questions work ("Đăng ký thường trú cần những
  giấy tờ gì?"); what the citation chips mean; what follow-up questions
  work and don't work (short context-free questions may give poor results);
  `[SCREENSHOT: chat widget showing a legal Q&A response with citation chips]`
- **Tính năng 2: Đọc CCCD và điền tờ khai tự động**: how to navigate to
  a procedure page; how to use the CCCD upload card; what "Độ chính xác:
  X%" means; how to review and correct auto-filled fields; how to submit
  the form; tracking code explanation;
  `[SCREENSHOT: procedure page with OCR upload card and auto-filled form]`
- **Tính năng 3: Tra cứu thứ tự thủ tục**: how to ask about procedural
  dependencies in the chat; example query: "Tôi muốn xác nhận thông tin
  cư trú, cần làm gì trước?"; expected response format;
  `[SCREENSHOT: chat response showing procedure dependency resolution]`
- **Giới hạn hệ thống** (known limitations for users):
  - Chỉ hỗ trợ các thủ tục cư trú (thường trú, tạm trú, xác nhận) —
    không hỗ trợ các thủ tục hành chính khác
  - OCR yêu cầu ảnh CCCD rõ nét, đủ sáng; ảnh mờ hoặc bị che khuất có
    thể không đọc được
  - Thông tin pháp lý chỉ bao gồm các văn bản đã được nhập vào hệ thống
  - Hệ thống là bản mô phỏng — không kết nối với cơ sở dữ liệu dân cư
    thực tế của chính phủ

### Definition of Done

- [ ] `docs/INSTALLATION.md` with complete step-by-step instructions for
      a fresh Windows 11 machine
- [ ] `docs/INSTALLATION.md` covers all 10+ steps from prerequisites to
      verification test
- [ ] All paths and commands in `INSTALLATION.md` are correct for the actual
      project structure (Windows paths verified)
- [ ] `docs/USER_GUIDE.md` covering all three main features
- [ ] `USER_GUIDE.md` written primarily in Vietnamese for citizen-facing
      sections
- [ ] At least 3 `[SCREENSHOT: ...]` placeholders clearly marked with
      descriptive captions
- [ ] `INSTALLATION.md` mental dry-run: following it step-by-step from a
      clean environment reaches a working system
- [ ] `USER_GUIDE.md` known limitations section is accurate and honest —
      does not overclaim system capabilities

### Notes / Constraints

- The `[SCREENSHOT: ...]` placeholders are acceptable if live screenshots
  cannot be taken during this task. Each placeholder must include a precise
  description of what should be captured so it can be replaced by an actual
  screenshot later.
- `INSTALLATION.md` is a technical document — use code blocks for all
  commands. `USER_GUIDE.md` is a citizen-facing document — avoid technical
  jargon (LangGraph, Qdrant, MinIO) in citizen-facing sections.
- Do not duplicate content between `README.md` and `INSTALLATION.md` —
  `README.md` is a project overview; `INSTALLATION.md` is a step-by-step
  guide with troubleshooting detail. Where they overlap (e.g., the
  migration command), `INSTALLATION.md` provides more context on expected
  output and common failure modes.
- The "Tính năng 2" section of the user guide depends on TASK-APP-02
  (download link) and TASK-APP-06 (loading indicators) being implemented.
  If those tasks are not yet done, document the current state accurately
  and add a note "Tính năng đang được cải tiến" rather than describing a
  future state.

---

## TASK-APP-13: Fix image upload — chat widget and procedure pages

**Priority:** Critical

### Goal

Image upload is broken in two places and must be fixed for the OCR demo to
work end-to-end.

**Problem A — Chat widget paperclip:** `streamChat` in `client.ts` accepts a
`file?: File` parameter (line 16) but the function body sends only
`JSON.stringify({ session_id: sessionId, message: message })` (lines 19–25)
— the `file` argument is silently dropped and never reaches the backend.
When the user attaches a CCCD image and sends a message, the image is lost
before any network call is made.

**Problem B — Procedure page OCR card verification:** The OCR upload card
was implemented on `dang-ky-thuong-tru/page.tsx` in a prior task and
appears correctly wired (it reads `sessionId` from `useChatStore` and calls
`api.documents.upload(file, sessionId)`), but the other two procedure pages
(`dang-ky-tam-tru`, `xac-nhan-cu-tru`) have not been verified to have the
same complete implementation. Inconsistencies in field mapping, session_id
handling, or missing `applyAIExtraction` calls would silently break OCR
pre-fill on those pages.

### Root cause for Problem A

The `streamChat` function was refactored from `FormData` to JSON body (to
fix a 422 error — see PROJECT_STATUS.md v3.3). During that refactor, file
handling was dropped. The correct fix is a **two-step send flow**: upload
the file first (which stores it in MinIO and saves `uploaded_document_path`
in the Redis session), then send the chat message as JSON. The chat endpoint
at `app/api/v1/chat.py` line 99 already reads the fallback:
`"uploaded_image_path": body.image_path or session.uploaded_document_path`
— so the session-based path is the intended mechanism.

### Inputs

- `frontend/src/lib/api/client.ts` — `streamChat()` (lines 13–46): accepts
  `file?: File` but does not send it. `api.documents.upload()` (lines 67–71):
  already sends `FormData` with `file` and `session_id` correctly — this
  function is fine and should be called from `handleSend`.
- `frontend/src/components/chat/ChatWidget.tsx` — `handleSend` callback
  (lines 63–105): line 81 passes `uploadedFile?.file` to `streamChat`, which
  ignores it. The `uploadedFile` state is cleared at line 68 — must be
  preserved until after the upload call.
- `frontend/src/app/thu-tuc/dang-ky-thuong-tru/page.tsx` — reference
  implementation. `handleOcrUpload()` reads `sessionId` from `useChatStore`
  (line 25), calls `api.documents.upload(file, sessionId)` (line 38), and
  calls `store.applyAIExtraction(FORM_TYPE, extracted)` (line 69). Verify
  this pattern before using as a template.
- `frontend/src/app/thu-tuc/dang-ky-tam-tru/page.tsx` and
  `frontend/src/app/thu-tuc/xac-nhan-cu-tru/page.tsx` — read both in full
  before writing any output. Do not assume they mirror `thuong-tru` — audit
  each one independently.
- `frontend/src/lib/stores/formStore.ts` — `applyAIExtraction(formType,
  extracted)` (line 37): takes
  `Partial<Record<keyof ResidenceFormData, { value: string; confidence: number }>>`.
  Sets `aiHighlight: true` for each AI-filled field automatically (line 89).
  `setFieldValue(formType, fieldKey, value, source, confidence)` (line 70):
  sets `aiHighlight: source === 'ai'`. Use `applyAIExtraction` for bulk OCR
  results — not individual `setFieldValue` calls.

### Outputs

**Problem A fix — `frontend/src/components/chat/ChatWidget.tsx`:**

Rewrite `handleSend` so that when `uploadedFile` is set, the file is uploaded
before the chat message is sent:

```typescript
const handleSend = useCallback(async () => {
  const text = input.trim()
  if (!text || isStreaming) return

  setInput('')
  addMessage({ role: 'user', content: text, citations: [] })

  const assistantId = addMessage({
    role: 'assistant', content: '', citations: [], isStreaming: true,
  })
  setStreaming(true)

  try {
    // Step 1: upload file if attached (stores in session so chat can read it)
    if (uploadedFile) {
      try {
        await api.documents.upload(uploadedFile.file, sessionId)
      } catch {
        updateMessage(assistantId, {
          content: 'Không thể tải lên tệp. Vui lòng thử lại.',
          isStreaming: false,
        })
        setStreaming(false)
        return   // do NOT proceed to chat if upload fails
      }
      setUploadedFile(null)   // clear after successful upload
    }

    // Step 2: send chat message as JSON (backend reads uploaded_document_path
    //         from Redis session — no need to send the file again)
    for await (const chunk of streamChat(sessionId, text)) {
      // ... existing chunk handling unchanged ...
    }
  } catch (err) {
    // ... existing error handling unchanged ...
  } finally {
    updateMessage(assistantId, { isStreaming: false })
    setStreaming(false)
  }
}, [input, isStreaming, sessionId, uploadedFile, addMessage, updateMessage,
    setStreaming, setUploadedFile])
```

Remove the `file` parameter from the `streamChat` call — `streamChat` should
be called as `streamChat(sessionId, text)` with no third argument. The
`streamChat` function signature in `client.ts` may retain the optional
parameter to avoid breaking callers, but it must not be relied upon.

**Problem B fix — procedure pages:**

For each of the three procedure pages, verify and ensure the following pattern
is present in `handleOcrUpload`:
1. `const { sessionId } = useChatStore()` is called at the top of the
   component — not inside the handler function
2. `api.documents.upload(file, sessionId)` is called with the chat store
   session ID (not a locally generated ID)
3. On `result.status === 'success'`, `store.applyAIExtraction(FORM_TYPE,
   extracted)` is called with an `extracted` dict that maps every available
   `PersonalData` field to its corresponding `ResidenceFormData` key:

   | `PersonalData` field | `ResidenceFormData` key |
   |---|---|
   | `full_name` | `ho_ten` |
   | `date_of_birth` (formatted DD/MM/YYYY) | `ngay_sinh` |
   | `id_number` | `so_cccd` |
   | `gender` | `gioi_tinh` |
   | `raw_address` or formatted `permanent_address` | `noi_thuong_tru_cu` |

   The field mapping keys for `tam-tru` and `xac-nhan` forms may differ —
   read the respective schemas in `app/schemas/form.py` and the form field
   names rendered in each page before writing the mapping.

4. On `result.status === 'partial'`, show the error message from TASK-APP-05
   and do NOT call `applyAIExtraction` (partial result means field values are
   unreliable).

### Definition of Done

- [ ] Chat widget paperclip attaches a file; on send, `api.documents.upload`
      is called first, then `streamChat` is called as JSON — in that order,
      verified by browser network tab
- [ ] If `api.documents.upload` fails, the chat message is NOT sent and an
      inline error is shown in the assistant bubble; `uploadedFile` is not
      cleared so the user can retry
- [ ] `session_id` from `useChatStore()` is passed to every `api.documents.upload`
      call on all three procedure pages
- [ ] Successful OCR on `thuong-tru` page pre-fills `ho_ten`, `ngay_sinh`,
      `so_cccd`, `gioi_tinh`, `noi_thuong_tru_cu` with `source='ai'`
- [ ] AI-filled fields display the visual indicator (gold/highlighted border
      or badge) per `formStore`'s `aiHighlight: true` behaviour
- [ ] `dang-ky-tam-tru` and `xac-nhan-cu-tru` pages have the complete OCR
      upload pattern — verified by reading each file in full before marking done
- [ ] `status='partial'` response shows actionable error message on all three
      pages; no field values are written to the form store on partial result
- [ ] Manual smoke test: upload a `category_1_clean_qr` image from
      `backend/data/mock_documents/` → fields fill in the form → visual
      indicator visible on filled fields

### Notes / Constraints

- `uploadedFile` must be cleared **after** the upload call succeeds, not
  before. The current code (line 68 in `ChatWidget.tsx`) clears it
  unconditionally at the top of `handleSend` — this must change.
- Do not pass `file` as a third argument to `streamChat` in the new flow.
  If you keep the parameter in `streamChat`'s signature for backwards
  compatibility, add a comment: `// file intentionally unused — upload via
  api.documents.upload before calling streamChat`.
- The two-step flow means two sequential HTTP requests per message-with-file.
  The upload request typically takes 2–10 seconds (OCR). During this time
  the loading dots in the assistant bubble are already showing — no additional
  UI indicator is required for the upload step itself.
- The `applyAIExtraction` carry-forward merge rule (higher confidence wins)
  means calling it with lower-confidence data will not overwrite existing
  high-confidence fields. This is the correct behaviour — do not replace it
  with individual `setFieldValue` calls that bypass the merge logic.

---

## TASK-APP-14: Implement GET /api/v1/procedures/{id}/plan endpoint

**Priority:** High

### Goal

`GET /api/v1/procedures/{procedure_id}/plan` is currently a stub that raises
`NotImplementedError` (`app/api/v1/procedures.py` line 34). This endpoint is
the programmatic representation of the procedural dependency DAG — a caller
sends a procedure code (e.g., `TTHC-CR-002`) and receives an ordered list
of steps the citizen must complete, in topological order, with completion
status for each.

Without this endpoint, the procedure plan is only accessible through the
AI chat flow. Implementing it as a REST endpoint enables: (a) the frontend
to display a static procedure roadmap without requiring a chat session, (b)
evaluation of the DAG logic independently from the AI pipeline, and (c)
use-case UC-003 to be demonstrable from `curl` or the `/docs` Swagger UI.

Additionally, `GET /api/v1/procedures/` (list all) must be implemented to
allow evaluators to discover the seeded procedures without a database client.

### Inputs

Read these files before writing:
- `backend/app/api/v1/procedures.py` — all 5 stubs (lines 1–43). The existing
  `response_model=ProcedureExecutionPlan` on `get_procedure_plan` is already
  set — verify it matches the desired output or create a richer response schema.
- `backend/app/schemas/procedure.py` — `ProcedureStep` (has `procedure_id`,
  `procedure_name`, `status`, `order` — does NOT have an `is_target` field),
  `ProcedureExecutionPlan` (`target_procedure_id`, `steps`, `missing_documents`),
  `ProcedureRead` (has `id: uuid.UUID`, `code: str`, `name: str`, etc.).
- `backend/app/core/procedure_graph.py` — `resolve_execution_plan()` signature:
  `(target_procedure_id: str, all_dependencies: list[ProcedureDependency],
  completed_ids: set[str], procedure_names: dict[str, str]) -> ProcedureExecutionPlan`.
  This is a pure synchronous function — do not call it inside an `async`
  route without reading the CLAUDE.md warning about CPU-bound calls.
- `backend/app/models/` AND `backend/alembic/versions/0001_initial_schema.py`
  — read these **together** before writing any query. The `procedures` table
  has a UUID primary key (`id`) and a string `code` field (e.g., `"TTHC-001"`).
  Critical: verify what `procedure_dependencies` stores in its `procedure_id`
  and `depends_on_procedure_id` columns — UUID or string code.
  `resolve_execution_plan()` builds its adjacency list keyed by these strings;
  if UUIDs are stored but string codes are expected, the topological sort
  produces wrong results silently — no runtime error, just an incorrect or
  empty execution plan. Read the migration and graph code together before
  writing a single line of the endpoint.
- `backend/alembic/versions/0001_initial_schema.py` — confirm the exact
  column types in `procedures` and `procedure_dependencies` tables.
- `backend/app/dependencies.py` — `get_db()` for the async DB session.

### Outputs

1. `backend/app/api/v1/procedures.py` — implement two endpoints:

   **`GET /api/v1/procedures/`:**
   - Query `SELECT id, code, name, domain, description FROM procedures`
   - Return `list[ProcedureRead]` — use the existing schema
   - Add `db: AsyncSession = Depends(get_db)` parameter
   - On DB error: return HTTP 500 with Vietnamese message

   **`GET /api/v1/procedures/{procedure_id}/plan`:**
   - `procedure_id` path parameter is the string `code` (e.g., `"TTHC-CR-002"`),
     not a UUID — the agent state and router use codes, not UUIDs
   - Query 1: check `procedures` table for a row where `code = procedure_id`.
     If not found → 404 `{"detail": "Không tìm thấy thủ tục với mã này."}`
   - Query 2: fetch all `procedure_dependencies` rows. Build
     `list[ProcedureDependency]` from them. Verify whether the DB stores
     codes or UUIDs in `procedure_id`/`depends_on_procedure_id` columns —
     the objects passed to `resolve_execution_plan` must match whatever
     `target_procedure_id` string format the graph expects.
   - Query 3: fetch all procedure names to build
     `procedure_names: dict[str, str]` (code → name)
   - Call `resolve_execution_plan(procedure_id, all_dependencies,
     completed_ids=set(), procedure_names=procedure_names)` in
     `asyncio.run_in_executor(None, ...)` — it is synchronous and
     CPU-bound; do not call it bare in an async route handler.
   - Return the `ProcedureExecutionPlan` Pydantic model directly as JSON.
     The `is_target` field mentioned in the task description does not exist
     in `ProcedureStep` — either add `is_target: bool = False` to
     `ProcedureStep` in `schemas/procedure.py` (preferred, one migration-free
     field addition), or identify the target step in the response by
     `procedure_id == target_procedure_id` in the frontend.

2. `backend/app/schemas/procedure.py` — if `is_target` is added to
   `ProcedureStep`, document the change. If not added, add a comment
   explaining that `target_procedure_id` in `ProcedureExecutionPlan`
   is the canonical way to identify the target step.

3. `backend/tests/unit/test_procedures_endpoint.py` (new file) — unit tests
   for both endpoints with a mocked `AsyncSession`:
   - `test_list_procedures_returns_all_seeded`: mock DB returning 7 rows
     (3 housing + 2 civil_registration + 2 adoption), assert response length
   - `test_get_plan_unknown_procedure_returns_404`: mock DB returning no row
     for `code = "TTHC-NOTEXIST"`, assert HTTP 404
   - `test_get_plan_tthc_cr002_includes_cr001`: mock DB with TTHC-CR-002 and
     its dependency on TTHC-CR-001, assert the response `steps` list contains
     TTHC-CR-001 with `status="pending"` before TTHC-CR-002
   - `test_get_plan_tthc_ad002_includes_ad001`: same pattern for adoption domain
   - `test_get_plan_completed_step_marked_completed`: mock `completed_ids`
     containing TTHC-CR-001, assert TTHC-CR-001 `status="completed"` in plan

### Definition of Done

- [ ] `GET /api/v1/procedures/` returns all seeded procedures as JSON list
- [ ] Unknown procedure code returns HTTP 404 with Vietnamese message
      `"Không tìm thấy thủ tục với mã này."`
- [ ] `GET /api/v1/procedures/TTHC-CR-002/plan` returns a steps list where
      TTHC-CR-001 appears before TTHC-CR-002 with the correct dependency
      structure
- [ ] `GET /api/v1/procedures/TTHC-AD-002/plan` returns a steps list where
      TTHC-AD-001 appears as a prerequisite step
- [ ] Response includes Vietnamese `procedure_name` values from the DB (not
      just the raw code string as a fallback)
- [ ] Unit tests in `test_procedures_endpoint.py` pass: list endpoint, 404
      case, TTHC-CR-002 dependency, TTHC-AD-002 dependency
- [ ] `resolve_execution_plan` is called via `run_in_executor` — not bare
      in the async route handler
- [ ] Endpoint is reachable and documented at `http://localhost:8000/docs`
      (FastAPI auto-generates Swagger)

### Notes / Constraints

- The path conflict risk: FastAPI router will attempt to match
  `GET /procedures/{procedure_id}` before `GET /procedures/{procedure_id}/plan`
  if registered in the wrong order — register the `/plan` sub-route before
  the `/{procedure_id}` route, or verify FastAPI's longest-match routing
  handles this correctly (it does, but verify).
- **UUID vs code string — silent failure risk.** If `procedure_dependencies`
  stores UUID values in `procedure_id`/`depends_on_procedure_id` but
  `resolve_execution_plan()` receives those UUIDs as the string keys it
  uses for the adjacency list, `topological_sort()` will return an incorrect
  or empty execution plan with **no runtime error** — the sort completes
  successfully but produces wrong results. This is the most likely
  implementation bug for this endpoint. Read `0001_initial_schema.py` and
  `procedure_graph.py` together before writing a single line of query code.
  If UUIDs are stored, the DB query must join to `procedures` to resolve
  codes; the `ProcedureDependency` objects passed to `resolve_execution_plan`
  must contain `code` strings, not UUIDs.
- `completed_ids` for this endpoint should default to `set()` — the plan
  endpoint is a static view of the DAG without session context. A future
  enhancement could accept `session_id` as a query parameter to show
  personalised completion status, but that is out of scope here.
- `ProcedureRead.id` is a `uuid.UUID` — Pydantic serialises this as a UUID
  string. Verify the `model_config = {"from_attributes": True}` is set
  correctly to map ORM attributes.
- Do not implement `POST /` (create procedure) or `GET /{id}/dependencies`
  in this task — they remain stubs. Only list and plan are required.

---

## TASK-APP-15: Conversation history compaction

**Priority:** Medium

### Goal

The current history management in `RedisService.save_session()` (line 101:
`data.conversation_history[-_MAX_HISTORY_TURNS:]`) silently drops the oldest
turns when a session exceeds 6 turns. In a long session — such as a citizen
asking multiple follow-up questions about a procedure — the first question
and its answer (which may have established the citizen's jurisdiction,
procedure intent, and personal data context) are lost entirely. This causes
the system to "forget" earlier context and ask redundant clarifying questions.

The target behaviour: when history exceeds the 6-turn window, condense the
oldest turns into a single compact summary entry rather than discarding them.
The summary is prepended to the kept history so the LLM always has semantic
context of the full session without the full token cost.

### Current behaviour (to preserve)

`redis_service.py` line 101: `trimmed_history = data.conversation_history[-_MAX_HISTORY_TURNS:]`

The existing 6-turn trim tests in `tests/unit/test_redis_service.py` must
still pass after this change.

### Inputs

- `backend/app/services/redis_service.py` — `save_session()` (lines 98–111).
  `_MAX_HISTORY_TURNS = 6` (line 24). The method is `async`. No compaction
  logic exists. `_compact_history` must be added as a new `async` method on
  `RedisService`.
- `backend/app/services/llm.py` — `LLMService.async_invoke(system, messages,
  max_tokens)` is the LLM call interface. Do not import `LLMService` at
  module level in `redis_service.py` — use a lazy import inside
  `_compact_history` or accept `LLMService` as an optional parameter to
  avoid any risk of circular imports at startup.
- `backend/app/schemas/session.py` — `SessionData.conversation_history:
  list[dict]` (line 20). Each entry is `{"role": "user"|"assistant",
  "content": str}`. The synthetic summary entry must use `role: "assistant"`
  with a fixed prefix `"Tóm tắt trước đó: "` on the content. Do NOT use
  `role: "system"` — Anthropic and Gemini only accept `"system"` as a
  top-level parameter, not as an entry inside the `messages` array; passing
  it there raises an API error. Using `"assistant"` keeps the history
  structurally uniform and requires no special handling in `synthesizer_node`
  or anywhere else the history is consumed.
- `backend/tests/unit/test_redis_service.py` — existing 9 tests that must
  continue to pass. The test for `save_session` history trim must be audited
  to ensure it still tests the correct behaviour after compaction is added.

### Implementation design

Add a new `async` method to `RedisService`:

```python
async def _compact_history(
    self,
    history: list[dict],
    max_turns: int = 6,
    llm_service=None,   # type: LLMService | None — lazy import avoids circ dep
) -> list[dict]:
    """Compact history exceeding max_turns into a summary + recent turns.

    Returns history unchanged if len(history) <= max_turns.
    """
    if len(history) <= max_turns:
        return history

    # Turns to compact: everything older than the most recent (max_turns - 1) turns
    cutoff = len(history) - (max_turns - 1)
    turns_to_compact = history[:cutoff]
    recent_turns = history[cutoff:]

    if llm_service is not None:
        # LLM path: summarise in Vietnamese
        compact_text = "\n".join(
            f"{t['role'].upper()}: {t['content']}" for t in turns_to_compact
        )
        summary = await llm_service.async_invoke(
            system=(
                "Hãy tóm tắt đoạn hội thoại dưới đây thành 2-3 câu bằng tiếng Việt, "
                "ghi lại thông tin quan trọng như thủ tục đã hỏi, thông tin cá nhân "
                "đã xác nhận, và kết quả của cuộc trò chuyện. "
                "Chỉ trả về bản tóm tắt, không giải thích thêm."
            ),
            messages=[{"role": "user", "content": compact_text}],
            max_tokens=256,
        )
    else:
        # Fallback: concatenate user messages
        user_msgs = [t["content"] for t in turns_to_compact if t.get("role") == "user"]
        summary = " | ".join(user_msgs[:3])

    synthetic = {"role": "assistant", "content": f"Tóm tắt trước đó: {summary}"}
    return [synthetic] + recent_turns
```

Update `save_session()` to call `_compact_history` instead of the bare slice:

```python
async def save_session(self, session_id: str, data: SessionData) -> None:
    compacted = await self._compact_history(data.conversation_history)
    data = data.model_copy(update={
        "conversation_history": compacted,
        "updated_at": datetime.utcnow(),
    })
    # ... rest of method unchanged ...
```

### Outputs

1. `backend/app/services/redis_service.py` — add `_compact_history` async
   method (full implementation per design above). Update `save_session()` to
   call `_compact_history` instead of direct slicing.
2. `backend/app/agents/nodes/synthesizer.py` — audit `conv_history` handling
   (line 240): `messages = conv_history + [{"role": "user", "content": user_msg}]`.
   The `"assistant"` role is universally supported in the messages array by
   both Anthropic and Gemini — no special handling required. Add a comment
   in `synthesizer_node` noting that the first history entry may be a
   compaction summary (role `"assistant"`, content prefixed with
   `"Tóm tắt trước đó: "`) and that this is intentional.
3. `backend/tests/unit/test_redis_service.py` — add new tests:
   - `test_compact_history_no_op_under_threshold`: 6 or fewer turns → returns
     unchanged list (no LLM call)
   - `test_compact_history_fires_at_turn_7`: 7 turns input → returns list of
     length ≤ 7 (1 summary + 6 recent) with LLM mocked
   - `test_compact_history_fallback_no_llm`: 8 turns, `llm_service=None` →
     returns list of length ≤ 7; summary entry `role` is `"assistant"`;
     content starts with `"Tóm tắt trước đó:"` prefix
   - `test_compact_history_boundary_exactly_max`: exactly `max_turns` turns
     → returns unchanged (no summary prepended)
   - `test_save_session_calls_compact`: mock `_compact_history` and assert it
     is awaited in `save_session()` — verifies the wiring

### Definition of Done

- [ ] `_compact_history` method implemented and `async`
- [ ] Compaction fires when `len(history) > max_turns` (6); returns
      unchanged list when `len(history) <= max_turns`
- [ ] LLM-based Vietnamese summary used when `llm_service` is provided
- [ ] Plain concatenation of user messages used as fallback when
      `llm_service` is None
- [ ] Compacted history never exceeds `max_turns + 1` entries
      (1 synthetic summary + 6 recent turns)
- [ ] Synthetic summary entry uses `role: "assistant"` and prefix
      `"Tóm tắt trước đó: "` — verified not to cause API errors with both
      Anthropic and Gemini backends (standard role, no special handling)
- [ ] All 5 new unit tests pass
- [ ] All 9 existing `test_redis_service.py` tests still pass
- [ ] No circular import introduced between `redis_service.py` and `llm.py`
      (verified by running `python -c "from app.services.redis_service import RedisService"`)

### Notes / Constraints

- `save_session()` is called from `chat.py` line 158 in a try/except that
  logs and continues on failure — compaction LLM errors must propagate up
  so `save_session` catches them and logs a warning rather than crashing
  the request. Wrap the `_compact_history` call in a try/except inside
  `save_session` and fall back to the raw 6-turn trim if compaction raises.
- The `_compact_history` method is `async` but `save_session` is also
  `async` — the `await` is straightforward. Do not use
  `asyncio.run_in_executor` for the LLM call; `llm.async_invoke` is already
  async.
- Compaction adds 1–2 LLM API calls per session save once the threshold is
  exceeded. This increases latency for the `save_session()` call from ~10ms
  (Redis write) to ~1–3s (LLM call + Redis write). Because `save_session`
  is non-fatal (errors are caught in `chat.py`), this latency does not block
  the SSE response — it only delays the next turn's context being persisted.
  Document this trade-off in a comment in the implementation.
- On Gemini free tier (5 req/min), the compaction LLM call consumes one of
  the 5 rate-limited requests per minute. If the user sends messages rapidly
  enough to trigger both a chat LLM call and a compaction call within 12
  seconds, a 429 may be returned by Gemini for the compaction call. The
  fallback (catch → plain concatenation) handles this gracefully.
- The design above uses `llm_service=None` by default so existing callers
  of `_compact_history` in tests can pass `None` without needing an LLM
  mock. When called from `save_session`, `llm_service` should also be
  `None` for now (plain concatenation is sufficient for the DoD). The LLM
  path is implemented and tested but activated only when a `LLMService`
  instance is explicitly injected — this keeps `save_session` fast by
  default and makes the LLM-enhanced version opt-in.
