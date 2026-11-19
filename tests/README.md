# Tests

Headless-Chrome checks (Playwright for Python) that load `extension.js` into a page with a fake `marinara` runtime and mock Marinara, SpicyAPI and NanoGPT. Nothing real is called, and the keys are fake (`spicy-test-key`, `nano-test-key`).

```sh
pip install playwright pillow && python -m playwright install chromium
python tests/test_full_flow.py "extension/Chroma Likeness" out-full.png
python tests/test_arena.py     "extension/Chroma Likeness" out-arena.png
python tests/test_roleplay.py  "extension/Chroma Likeness" out-rp.png
python tests/test_continuity.py "extension/Chroma Likeness" out-cont.png
```

Each script prints its results and ends with `ERRORS: []` when the page threw nothing. The second argument is where it saves a screenshot.

| Test | Covers |
|---|---|
| `test_full_flow.py` | Settings, test generation and editing, Generate and post, photo sets, Another, Animate, locked photos and Unlock, dares, the reaction loop, closet, album and morning photo (clock pinned to 08:15) |
| `test_arena.py` | Conversation vs Roleplay detection, Auto-configure, the video switch |
| `test_continuity.py` | Wardrobe thumbnails, the outfit folder, 👎 on an outfit photo (description rewritten, correction learned and used in the next picture, Undo), photos taken by side characters, keys saved in Marinara and restored in a fresh browser, Reload from Marinara, contextual photos starting on their own, wardrobe save and wear, a scene linked to its Chat (outfit and mood carried, first reply pictured, outfit photo as image 2), End scene (outfit back, scene photo posted in the Chat), status line |
| `test_roleplay.py` | The user's own character taking a photo in Roleplay, following whichever chat is open, 📷 Picture the last reply, attaching to the reply via PATCH `/extra`, chat-view reload, retry when the writer answers in prose |

The tests use a mocked version of Marinara's page, not the real app. Check anything that depends on Marinara's chat view in the real app.
