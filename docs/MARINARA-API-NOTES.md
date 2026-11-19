# API notes

What the extension relies on. These were worked out from Marinara's source, pull requests and live testing during development. Check them against current Marinara if anything breaks.

## Marinara Engine (same-origin REST)

Send the headers `x-marinara-csrf: 1` and `X-Admin-Secret` (taken from localStorage `marinara_admin_secret`).

| Route | Use |
|---|---|
| `GET /api/chats`, `GET /api/chats/:id` | `mode` (conversation, roleplay or game), `characterIds`, `connectionId`, `metadata` |
| `PATCH /api/chats/:id/metadata` | Chat options |
| `GET /api/chats/:id/messages?limit=N` | Recent messages. `extra` is a JSON string with `attachments`. Roles include assistant, narrator, character and model |
| `POST /api/chats/:id/messages` | `{role, characterId, content, extra:{attachments:[{type:"image"or"video", url, galleryId, name, prompt, durationSeconds}]}}` |
| `PATCH /api/chats/:chatId/messages/:messageId/extra` | Adds pictures to an existing message (Roleplay). The extension sends the whole merged `extra` object, then the `{extra}` form if that doesn't work, and reads the message back to confirm |
| `PATCH /api/chats/:chatId/messages/:messageId` | Edits content only |
| `GET /api/connections`, `GET /api/connections/:id/models` | Fills the model dropdowns |
| `GET/PATCH /api/characters/:id` | Card data. PATCH takes `{data:{extensions}, skipVersionSnapshot, versionSource}`; it deep-merges, and `null` deletes |
| `GET /api/gallery/:chatId`, `POST /api/gallery/:chatId/upload` | Gallery. Upload is FormData with provider, model, prompt and file. The extension's rows have provider `chroma-likeness` |
| `GET /api/gallery/file/:chat/:file` | Image files |

- Server-side extensions are sandboxed with no network access, which is why this one runs in the client with full page access.
- Marinara's own pictures (Illustrator, selfies, scene images) are built from the avatar and the card's appearance, and use the chat's image connection. Chat options: Send Avatar References, Attach Card Appearance.
- A scene that a character invites you to in a Conversation becomes a new Roleplay chat.

## SpicyAPI

- Jobs: `POST https://api.spicyapi.ai/api/v1/jobs/createTask` with `{model, input}` and an `Idempotency-Key` header. It returns 202 with `data.taskId`. Then poll `GET /jobs/recordInfo?taskId=` until the state is succeeded, failed or expired. Results are at `data.output.assets[].url` and expire after about 20 minutes.
- Models: `GET /api/v1/models?includeSchema=1` (with the key) returns `inputSchema`. The public catalogue is `/console/v1/catalog/models?locale=en`.
- Uploads: `POST /api/v1/common/upload-url {contentType, bytes}`, then PUT to `uploadUrl` without the Authorization or Content-Length headers, then `POST /api/v1/files/{fileId}/commit`, which returns a `spicy://` URI. Images of 1 MiB or less can go as a data URI instead.
- Chat completions: `https://api.spicyapi.ai/v1/chat/completions`.
- Defaults:
  - Generation: `alibaba/z-image-spicy-pro/text-to-image`.
  - Editing: `bytedance/seedream-5.0-pro/edit` (up to 10 references), with `alibaba/qwen-image-spicy-edit/edit` as an alternative.
  - Video: `alibaba/wan-2.2-spicy/image-to-video`.

## NanoGPT

- Chat: `https://api.nano-gpt.com/api/v1/chat/completions`.
- Models: `GET /api/v1/models?detailed=true` gives `capabilities.vision`, `structured_output` and `reasoning`, and `pricing.prompt`.
- Key check: `POST /api/check-balance` with an `x-api-key` header.
- Models with structured output get `response_format: json_object`; if that's rejected, the request is retried without it. Reasoning models get `max_tokens` of at least 3000 and no temperature.
