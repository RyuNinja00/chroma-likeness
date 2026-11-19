# Briefing for Claude

You are picking up **Chroma Likeness**, a Marinara Engine personal extension. Read `README.md` for what it does, `docs/PROJECT-HISTORY.md` for why things are the way they are, and `docs/MARINARA-API-NOTES.md` before touching any API call.

## The user

- Uses Marinara Engine, mostly on a phone. Chats in both Conversation and Roleplay modes, including scene chats that Marinara creates from an invite in a Conversation.
- Uses NanoGPT as their main text model provider and SpicyAPI for pictures and video. Sogni was tried and dropped because the browser blocked it (CORS). Remove other providers rather than adding them back.
- Adult, uncensored use. Keep the adults-only anchor in every picture prompt.
- Has turned Marinara's Illustrator off in Chat and Roleplay: Likeness must make every picture itself. Don't rely on Illustrator, selfies or Marinara image connections.
- Wants things to work automatically: settings worked out from context, prompting that adapts to the model and chat type. Tests the extension live and reports what they see, often briefly ("no picture was produced"). Diagnose the cause from the code before changing it.

## Architecture (all in `extension.js`)

- Client runtime with `full_page_access`. The file is the body of an async function that receives `marinara` (`fetch`, `onCleanup`, `setInterval`, `setTimeout`, `clearTimeout`). Use those timers so Marinara can clean up.
- Storage, three layers:
  - `marinara.storage` (Marinara's per-extension storage) holds `config` (keys too), `lockedIndex`, `links`, and `state/`, `album/`, `lastScene/`, `link/` and `photos/` (each person's filed photos) entries. `store()` writes these through to it (debounced `patch`) and reads them from it first.
  - IndexedDB `marinara-chroma-likeness-v1` is a local cache, plus per-browser things: `jobs`, `watch`, references.
  - Card extensions on the character (`chromaLikeness…` keys) hold what should travel with the card: the heart, its traits, the closet.
- Model catalogues: SpicyAPI `/api/v1/models?includeSchema=1` (inputs are built from each model's schema, because unknown fields return a 400) and NanoGPT `/api/v1/models?detailed=true` (vision, structured output and reasoning flags).
- Main flows:
  - `render()`: generates or edits a picture via `spicyImage()`.
  - `deliver()` → `postMedia()`: puts the picture in the gallery, then into the chat. In Roleplay the picture is attached to the latest message via PATCH `/extra`; in Conversation it's posted as a separate message. Then `refreshChatView()`.
  - `poll()` → `linkChats()` (scene ↔ Chat links, `checkReturns()` after End scene) → `pollContext()` → `planPicture()`: the writer decides who to picture and how, and returns JSON read by `replyJson()`. That JSON includes outfits, mood, `wardrobeAdd` and `wear`, which `absorbState()` applies.
  - Picture rules: a photo taken in the story (`takesPhoto()` on the user's last message and the latest reply) is always pictured unless story pictures are off, with one insisting retry. Conversation uses `config.initiative`; Roleplay and Game use `config.story` (moments/often/photos/off). `setStatus()` records why each reply did or didn't get a picture, for the status line in `paintArena()`.
  - Closet items: `{outfit, title?, auto, picture?, pictures?, votes?, notes?, prevOutfit?, at}`. Saved (`auto:false`) items are never pruned. `picture` is the outfit's reference and thumbnail, passed to `render()` as `outfitRef` (image 2, clothes only) with `notes`. Chat state `outfitKeys` says which saved outfit each person wears (`wornItem()`), and `sceneState()` substitutes that item's current description. `deliver()` files solo pictures with the worn outfit. `rateOutfit()` learns from 👍/👎. `outfitReference()` picks the reference (♡ choice kept; otherwise likeness-👍 first, never likeness- or outfit-👎). Two-person pictures add both outfit pictures as images 3–4 when the model allows. Over-limit prompts keep learned likeness details and outfit notes, and shorten the scene first. The Wardrobe section and the outfit folder dialog (`#chroma-likeness-wardrobe`) are built by `paintWardrobe()` and `paintOutfit()`.
  - Reference pictures: the main heart plus up to 2 extra hearts (`profile.extras`, `toggleExtraHeart()`, `ref.extras` with blobs). `refCapacity(model)` is the single source for how many pictures a model takes: a stated list maximum, else 2 for lists, 1 for a single picture field, and 1 when the rules aren't loaded. `render(…, outfitRef, heartExtras)` fills that room in a fixed order (solo: main, extra 1, outfit, extra 2; pair: both mains, then outfits) and never exceeds it. `capacityText()` is shown under the editing model and in the folder.
  - Redo (`openRedo()`/`redoPicture()`): ✎ on photo cards and the chat hover toolbar; the new picture replaces the old attachment in its message via PATCH `/extra`. Photo notes: the planner returns `caption`, `why` and (Conversation) `text`; attachment `prompt` = caption + why; in Conversation the photo message's content is her `text` (`config.photoText`). Character Galleries: `addToCharacterGalleries()` uploads to `/characters/:id/gallery/upload`, falling back to `/gallery` (`config.charGallery`, `copied/<id>`), and reports refusals once.
  - `animatePicture()`, `makeSet()`, `maybeDaily()`, the closet, the album and dares. Locked photos were retired in 2.8.0: `shouldLock()` always returns false and the setting is hidden; old teasers can still be unlocked.
  - Panel layout: Settings, Chat and character, Contextual chat photos, Generate a picture, Recurring friends, Characters. The Characters section shows a thumbnail per character (`paintCharacters()`). `openPerson()` selects that character and shows `personPane` in the folder dialog. That pane holds the controls that used to be in the Gallery, Album and Wardrobe sections, which no longer exist. The outfit folder uses the same dialog, with a ← back button. `note()` also writes into the open folder (`mirrorOut`). Photo cards in `paint()` show this person's pictures in the selected chat plus their filed photos (`photos/<id>`) from other chats, with buttons in one icon row. Tests open folders via `.person-tile` and use `#chroma-likeness-wardrobe` locators.
- Chat type comes from `chatArena(id)` (`conversation` | `roleplay` | `game`) and controls style through `styleFor()`, `styleGuide()` and `composeScene()`.

## Conventions

- Bump `manifest.json`'s version for every user-visible change, and add a row to `docs/PROJECT-HISTORY.md` (problem, cause, fix) and update its version line.
- Keep a full copy of the previous `extension.js` before a big edit. Check it still parses: `node -e "new (Object.getPrototypeOf(async function(){}).constructor)('marinara', require('fs').readFileSync('extension/Chroma Likeness/extension.js','utf8'))"`.
- Avoid straight apostrophes inside single-quoted JS strings; the code uses ’. Write messages the user sees in plain words.
- Run all tests (see `tests/README.md`: four browser tests and `test_prompts.js`) before packaging. Package with `scripts/package.sh`, which builds `releases/Chroma-Likeness-Marinara-<version>.zip` with the `Chroma Likeness/` folder at the root.
- After installing a new ZIP, the user must re-approve the extension and reload the tab.

## Known gotchas

- `crypto.randomUUID` is missing on plain-HTTP LAN origins, so use `uid()`.
- A CSS `display:grid` rule beat `[hidden]`, so there's a `!important` rule in the CSS.
- Marinara's chat view caches its messages and won't show messages added through the API until it reloads. `refreshChatView()` finds the React Query client through the React fiber tree and invalidates that chat's queries. If it can't, it fires visibilitychange/focus.
- In Roleplay, a separate message holding only a picture can get lost if Marinara is still finishing the reply (agents, trackers), so the picture is attached to the reply instead.
- Contextual mode skips replies that Marinara has already pictured, to avoid double pictures.
- Contextual photos start by themselves (`autoWatch()`) once keys exist, unless `config.contextOff`. Tests must press the contextual-photos button only when it reads "Enable".
- Writer models tuned for roleplay sometimes reply in character instead of JSON. `replyJson()` is lenient, and `planPicture()` retries once.
