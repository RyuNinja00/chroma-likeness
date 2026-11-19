# Chroma Likeness

A personal extension for [Marinara Engine](https://github.com/Pasta-Devs/Marinara-Engine). It keeps a character looking like themselves in every picture. You "heart" a picture that looks right, rate later pictures 👍/👎, and the extension uses the heart as the reference while pose, place, outfit and mood change.

Pictures and video come from **SpicyAPI**. Text work (deciding when to take a photo, writing the picture prompt, describing the hearted picture) runs on **NanoGPT** or a SpicyAPI text model.

Current version: **2.5.5**. See [docs/PROJECT-HISTORY.md](docs/PROJECT-HISTORY.md) for every change and the reasons behind it.

## What it does

- **Likeness:** a hearted reference per character, stored on the character card, plus a short written description of how they look. 👍/👎 ratings add notes that guide later edits.
- **Context photos:** watches the open chat and pictures the moment when someone takes or sends a photo, or, if you allow it, on its own at charged moments. It works in Conversation, Roleplay and Game chats, and the style adapts to each: phone-camera realism in Conversation, scene shots in Roleplay.
- **Continuity:** remembers each character's current outfit and mood for each chat. Saved outfits go in a closet that's kept on the character card.
- **Extras:** photo sets, 📸 "Another" (the next shot in a series), dares, an album of favourites, locked photos with a blurred preview and 🔓 Unlock, moving photos (🎬 Animate, can be switched off), and morning and night selfies.
- **Prompt adaptation:** prompts are built from each model's own input schema, use a negative prompt (or an anatomy hint for models that don't take one), and are worded differently for tag-style and sentence-style models.

## Install

1. In Marinara, go to Settings → Addons → Personal Extensions and import `releases/Chroma-Likeness-Marinara-2.5.5.zip`. If you're building from source, run `scripts/package.sh` first and import the ZIP it makes.
2. Approve it. Marinara asks again after every change to the extension.
3. Reload the browser tab. The Marinara server doesn't need restarting.
4. Open the Likeness panel, add your SpicyAPI and NanoGPT keys, and press **Auto-configure**.

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

- Fixes from 2.5.3 to 2.5.5 (Roleplay pictures attached to the reply, chat view reload, retry when the writer's answer can't be read) passed the mocked tests but haven't yet been confirmed in a real Marinara Roleplay scene chat.
- Marinara's own Illustrator and selfie pictures use the avatar, not the heart. A "fix the likeness of Marinara's pictures" mode was designed but not built.
