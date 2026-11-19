# Briefing for Claude

You are picking up **Chroma Likeness**, a Marinara Engine personal extension. Read `README.md` for what it does, `docs/PROJECT-HISTORY.md` for why things are the way they are, and `docs/MARINARA-API-NOTES.md` before touching any API call.

## The user

- Uses Marinara Engine, mostly on a phone. Chats in both Conversation and Roleplay modes, including scene chats that Marinara creates from an invite in a Conversation.
- Uses NanoGPT as their main text model provider and SpicyAPI for pictures and video. Sogni was tried and dropped because the browser blocked it (CORS). Remove other providers rather than adding them back.
- Adult, uncensored use. Keep the adults-only anchor in every picture prompt.
- Wants things to work automatically: settings worked out from context, prompting that adapts to the model and chat type. Tests the extension live and reports what they see, often briefly ("no picture was produced"). Diagnose the cause from the code before changing it.

## Architecture (all in `extension.js`)

- Client runtime with `full_page_access`. The file is the body of an async function that receives `marinara` (`fetch`, `onCleanup`, `setInterval`, `setTimeout`, `clearTimeout`). Use those timers so Marinara can clean up.
- Storage: an IndexedDB database `marinara-chroma-likeness-v1` (settings, references, jobs), plus card extensions on the character (`chromaLikeness…` keys) for anything that should travel with the card: the heart, its traits, the closet.
- Model catalogues: SpicyAPI `/api/v1/models?includeSchema=1` (inputs are built from each model's schema, because unknown fields return a 400) and NanoGPT `/api/v1/models?detailed=true` (vision, structured output and reasoning flags).
- Main flows:
  - `render()`: generates or edits a picture via `spicyImage()`.
  - `deliver()` → `postMedia()`: puts the picture in the gallery, then into the chat. In Roleplay the picture is attached to the latest message via PATCH `/extra`; in Conversation it's posted as a separate message. Then `refreshChatView()`.
  - `poll()` → `pollContext()` → `planPicture()`: the writer decides who to picture and how, and returns JSON read by `replyJson()`.
  - `animatePicture()`, `makeSet()`, `maybeDaily()`, the closet, the album, dares and locked photos.
- Chat type comes from `chatArena(id)` (`conversation` | `roleplay` | `game`) and controls style through `styleFor()`, `styleGuide()` and `composeScene()`.

## Conventions

- Bump `manifest.json`'s version for every user-visible change, and add a row to `docs/PROJECT-HISTORY.md` (problem, cause, fix) and update its version line.
- Keep a full copy of the previous `extension.js` before a big edit. Check it still parses: `node -e "new (Object.getPrototypeOf(async function(){}).constructor)('marinara', require('fs').readFileSync('extension/Chroma Likeness/extension.js','utf8'))"`.
- Avoid straight apostrophes inside single-quoted JS strings; the code uses ’. Write messages the user sees in plain words.
- Run all three tests (see `tests/README.md`) before packaging. Package with `scripts/package.sh`, which builds `releases/Chroma-Likeness-Marinara-<version>.zip` with the `Chroma Likeness/` folder at the root.
- After installing a new ZIP, the user must re-approve the extension and reload the tab.

## Known gotchas

- `crypto.randomUUID` is missing on plain-HTTP LAN origins, so use `uid()`.
- A CSS `display:grid` rule beat `[hidden]`, so there's a `!important` rule in the CSS.
- Marinara's chat view caches its messages and won't show messages added through the API until it reloads. `refreshChatView()` finds the React Query client through the React fiber tree and invalidates that chat's queries. If it can't, it fires visibilitychange/focus.
- In Roleplay, a separate message holding only a picture can get lost if Marinara is still finishing the reply (agents, trackers), so the picture is attached to the reply instead.
- Contextual mode skips replies that Marinara has already pictured, to avoid double pictures.
- Writer models tuned for roleplay sometimes reply in character instead of JSON. `replyJson()` is lenient, and `planPicture()` retries once.
