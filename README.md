# Chroma Likeness

A personal extension for [Marinara Engine](https://github.com/Pasta-Devs/Marinara-Engine). It keeps a character looking like themselves in every picture. You "heart" a picture that looks right, rate later pictures 👍/👎, and the extension uses the heart as the reference while pose, place, outfit and mood change.

Pictures and video come from **SpicyAPI**. Text work (deciding when to take a photo, writing the picture prompt, describing the hearted picture) runs on **NanoGPT** or a SpicyAPI text model.

Current version: **2.6.0**. See [docs/PROJECT-HISTORY.md](docs/PROJECT-HISTORY.md) for every change and the reasons behind it.

## What it does

- **Does every picture itself:** Marinara's Illustrator can stay off in Chat and Roleplay. Contextual photos start on their own in whichever chat is open.
- **Likeness:** a hearted reference per character, stored on the character card, plus a short written description of how they look. 👍/👎 ratings add notes that guide later edits.
- **Context photos:** watches the open chat. In Chat (Conversation) it pictures photos you ask for or she sends, and optionally some on her own. In Roleplay and Game it pictures key story moments by default (configurable), including the first reply of a new scene. The style adapts: phone-camera realism in Conversation, scene shots in Roleplay.
- **Continuity:** remembers each character's current outfit and mood for each chat. When Marinara builds a scene from a Chat, the outfit and mood carry into the scene. After End scene they come back, with a photo from the scene posted in the Chat.
- **Wardrobe:** "add this to your wardrobe" saves a named, detailed outfit on the character card. "Put on the red dress" wears it. The outfit's first picture shows the clothes in later pictures.
- **Settings in Marinara:** keys and settings are kept in Marinara's storage for the extension, so clearing the browser doesn't lose them, and every device gets them. A status line shows what the extension is doing in each chat.
- **Extras:** photo sets, 📸 "Another" (the next shot in a series), dares, an album of favourites, locked photos with a blurred preview and 🔓 Unlock, moving photos (🎬 Animate, can be switched off), and morning and night selfies.
- **Prompt adaptation:** prompts are built from each model's own input schema, use a negative prompt (or an anatomy hint for models that don't take one), and are worded differently for tag-style and sentence-style models.

## Install

1. In Marinara, go to Settings → Addons → Personal Extensions and import `releases/Chroma-Likeness-Marinara-2.6.0.zip`. If you're building from source, run `scripts/package.sh` first and import the ZIP it makes.
2. Approve it. Marinara asks again after every change to the extension.
3. Reload the browser tab. The Marinara server doesn't need restarting.
4. Open the Likeness panel, add your SpicyAPI and NanoGPT keys, and press **Auto-configure**. Turn Illustrator off in your chats; Likeness makes the pictures.

`relay/likeness-relay.mjs` is an optional local relay, needed only if a provider blocks requests sent from the browser (CORS). Run `node relay/likeness-relay.mjs` and put its address in the Relay setting.

## Repository layout

| Path | What it is |
|---|---|
| `extension/Chroma Likeness/` | Source: `manifest.json`, `extension.js` (everything; about 157 KB), `extension.css` |
| `releases/` | The ZIP to import into Marinara, plus the original 1.7.0 for reference |
| `relay/` | Optional CORS relay |
| `tests/` | Headless-Chrome tests against mocked Marinara, SpicyAPI and NanoGPT |
| `docs/PROJECT-HISTORY.md` | Version-by-version history: each problem, its cause and the fix |
| `docs/MARINARA-API-NOTES.md` | The Marinara, SpicyAPI and NanoGPT details the code depends on |
| `CLAUDE.md` | Briefing for an AI assistant picking up the work |

## Open issues

- 2.6.0 passed the mocked tests but hasn't been confirmed in real Marinara yet. In particular, check that `marinara.storage` is available to this extension (the status line says where settings are stored) and that scene links are detected (the status line in a scene says so).
- Scene links are found by field name patterns because Marinara's exact metadata names aren't documented. If a scene isn't linked, check the scene chat's metadata.
