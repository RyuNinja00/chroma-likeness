import asyncio, base64, json, sys, io, re
from playwright.async_api import async_playwright
from PIL import Image, ImageDraw

EXT, OUT = sys.argv[1], sys.argv[2]
src = open(EXT + "/extension.js").read()
css = open(EXT + "/extension.css").read()
def png(color):
    im = Image.new("RGB", (512, 640), "white"); d = ImageDraw.Draw(im); d.ellipse((150, 150, 360, 420), fill=color)
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()
PORTRAIT, RESULT = png((200, 150, 120)), png((60, 170, 60))

page_html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div id="root"></div><div data-chat-composer data-chat-id="c1"></div><script>
window.__inval=[];(()=>{{const client={{getQueryCache(){{return{{}}}},invalidateQueries(o){{const keys=[["chats","c1","messages"],["chats","c2","messages"],["characters"]];window.__inval.push(keys.filter(k=>o.predicate({{queryKey:k}})).map(k=>k.join("/")).join(","));}}}};
const leaf={{memoizedProps:{{}}}};const prov={{memoizedProps:{{client}},child:leaf}};const top={{memoizedProps:{{}},child:{{memoizedProps:{{}},sibling:prov}}}};
document.getElementById("root")["__reactContainer$abc"]=top;}})();</script><script>
window.marinara = {{ fetch: (...a) => window.fetch(...a), onCleanup(){{}}, setInterval: (f,t)=>setInterval(f,Math.min(t,1500)),
  setTimeout: (f,t)=>setTimeout(f,Math.min(t,300)), clearTimeout: (t)=>clearTimeout(t) }};
window.__errors = []; window.addEventListener('error', e => __errors.push(String(e.message)));
window.addEventListener('unhandledrejection', e => __errors.push(String(e.reason)));
(async function(){{ {src}
}})().catch(e => __errors.push('init: ' + e));
</script></body></html>"""

MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200
SCHEMAS = {
    "alibaba/wan-2.2-spicy/image-to-video": {"type": "object", "required": ["prompt", "image_url"], "properties": {
        "prompt": {"type": "string"}, "image_url": {"type": "string"}, "duration_seconds": {"type": "integer", "enum": [8, 5]},
        "resolution": {"type": "string", "enum": ["480p", "720p"]}, "seed": {"type": "integer"}}},
    "alibaba/z-image-spicy-pro/text-to-image": {"type": "object", "required": ["prompt"], "properties": {
        "prompt": {"type": "string", "maxLength": 4000}, "aspect_ratio": {"type": "string", "enum": ["1:1", "3:4", "4:3", "9:16", "16:9"]}, "seed": {"type": "integer"}}},
    "bytedance/seedream-5.0-pro/edit": {"type": "object", "required": ["prompt", "image_urls"], "properties": {
        "prompt": {"type": "string"}, "image_urls": {"type": "array", "maxItems": 10, "items": {"type": "string"}},
        "aspect_ratio": {"type": "string", "enum": ["1:1", "2:3", "3:2", "3:4", "4:3"]}, "resolution": {"type": "string", "enum": ["1K", "2K"]}}},
}
MODELS = [
    {"model": "alibaba/z-image-spicy-pro/text-to-image", "displayName": "Z-Image Spicy Pro", "modality": "image", "tasks": ["text-to-image"], "startingPrice": 0.019, "inputSchema": SCHEMAS["alibaba/z-image-spicy-pro/text-to-image"]},
    {"model": "bytedance/seedream-5.0-pro/edit", "displayName": "Seedream 5.0 Pro Edit", "modality": "image", "tasks": ["image-edit"], "startingPrice": 0.036, "inputSchema": SCHEMAS["bytedance/seedream-5.0-pro/edit"]},
    {"model": "bytedance/seedream-5.0-pro/text-to-image", "displayName": "Seedream 5.0 Pro", "modality": "image", "tasks": ["text-to-image"], "startingPrice": 0.036},
    {"model": "wan/wan-2.2-spicy/image-to-video", "displayName": "Wan 2.2 Spicy", "modality": "video", "tasks": ["image-to-video"]},
    {"model": "alibaba/wan-2.2-spicy/image-to-video", "displayName": "Wan 2.2 Spicy", "modality": "video", "tasks": ["image-to-video"], "startingPrice": 0.08, "inputSchema": SCHEMAS["alibaba/wan-2.2-spicy/image-to-video"]},
    {"model": "spicy/roleplay-70b", "displayName": "Spicy Roleplay 70B", "modality": "text", "tasks": ["chat"]},
    {"model": "qwen/qwen3-vl-uncensored", "displayName": "Qwen3 VL Uncensored", "modality": "text", "tasks": ["chat", "vision"]},
]
state = {"char": {"name": "Alex", "extensions": {"imageAppearance": "Original look from the card", "imageAppearanceEnabled": True}},
         "gallery": [], "tasks": {}, "log": [], "inputs": [], "puts": [], "planner": "photo",
         "messages": [
                {"id": "m3", "role": "assistant", "characterId": "ch1", "content": "*laughs* Fine, here's one from the bar. Black lace, just for you.", "createdAt": "2026-11-18T10:03"},
                {"id": "m1", "role": "user", "content": "How's the party?", "createdAt": "2026-11-18T10:01"},
                {"id": "m2", "role": "user", "content": "Send me a pic of what you're wearing tonight?", "createdAt": "2026-11-18T10:02"}]}
def merge(a, b):
    for k, v in b.items():
        if v is None: a.pop(k, None)
        elif isinstance(v, dict) and isinstance(a.get(k), dict): merge(a[k], v)
        else: a[k] = v
    return a
def j(route, data, status=200):
    return route.fulfill(status=status, content_type="application/json", body=json.dumps(data), headers={"access-control-allow-origin": "*"})

async def handle(route):
    req, url = route.request, route.request.url
    if url.startswith("http://localhost:7860/api/"):
        path = url[len("http://localhost:7860/api"):]
        if path == "/chats": return await j(route, [{"id": "c1", "name": "DM chat", "characterIds": '["ch1"]', "mode": "conversation"}, {"id": "c2", "name": "Story", "characterIds": '["ch1"]', "mode": "roleplay"}])
        m = re.match(r"^/chats/(c\d)$", path)
        if m: return await j(route, {"id": m.group(1), "characterIds": '["ch1"]', "mode": "conversation" if m.group(1) == "c1" else "roleplay", "connectionId": "n1", "metadata": "{}"})
        path = re.sub(r"/(chats|gallery)/c2", r"/\1/c1", path)
        if path == "/connections": return await j(route, [
            {"id": "s1", "name": "SpicyAPI images", "provider": "image_generation", "model": "bytedance/seedream-5.0-pro/edit", "baseUrl": "https://api.spicyapi.ai/api/v1"},
            {"id": "n1", "name": "NanoGPT chat", "provider": "nanogpt", "model": "deepseek/x", "baseUrl": "https://nano-gpt.com/api/v1"}])
        if path == "/characters/ch1":
            if req.method == "PATCH":
                body = json.loads(req.post_data); merge(state["char"], body["data"]); state["log"].append("PATCH card " + ",".join(body["data"].get("extensions", {}).keys()))
            return await j(route, {"id": "ch1", "data": json.dumps({"data": state["char"]})})
        if path == "/gallery/c1/upload":
            gid = "g%d" % (len(state["gallery"]) + 2)
            raw = req.post_data_buffer or b""
            ext = "mp4" if b"likeness.mp4" in raw else "jpg" if b"likeness.jpeg" in raw else "png"
            state["log"].append("upload " + ext)
            item = {"id": gid, "url": "/api/gallery/file/c1/%s.%s" % (gid, ext), "chatId": "c1", "provider": "chroma-likeness", "model": "m", "prompt": "p", "createdAt": "2026-11-18T10:%02d" % len(state["gallery"])}
            state["gallery"].insert(0, item); return await j(route, item)
        if path.startswith("/gallery/file/"):
            return await route.fulfill(status=200, content_type="image/png", body=PORTRAIT)
        if path == "/gallery/c1": return await j(route, state["gallery"])
        if path.startswith("/chats/c1/messages/") and path.endswith("/extra") and req.method == "PATCH":
            mid = path.split("/")[4]; b = json.loads(req.post_data)
            for m in state["messages"]:
                if m["id"] == mid:
                    ex = json.loads(m.get("extra") or "{}") if isinstance(m.get("extra"), str) or not m.get("extra") else m["extra"]
                    ex.update(b); m["extra"] = json.dumps(ex)
                    state["log"].append("ATTACHED to %s (%s) %s" % (mid, m["role"], [x["url"].rsplit("/",1)[-1] for x in ex.get("attachments", [])]))
                    return await j(route, m)
            return await j(route, {"error": "no message"}, 404)
        if path == "/chats/c1/messages":
            b = json.loads(req.post_data); ex = b["extra"]
            if b["role"] == "user":
                state["log"].append("USER MESSAGE " + b["content"]); return await j(route, {"id": "u"})
            if b.get("content"): state["log"].append("WITH TEXT «" + b["content"][:50] + "»")
            n = len(state["messages"]) + 10
            state["messages"].append({"id": "p%d" % n, "role": "assistant", "characterId": "ch1", "content": b.get("content", ""), "extra": json.dumps(ex), "createdAt": "2026-11-18T11:%02d" % (n % 60)})
            state["log"].append("POSTED %s%s%s" % ([a["type"] + ":" + a["url"].rsplit("/", 1)[-1] + " «" + str(a.get("prompt"))[:45] + "»" for a in ex["attachments"]], " LOCKED" if ex.get("likenessLocked") else "", " UNLOCK" if ex.get("likenessUnlocked") else ""))
            return await j(route, {"id": "m"})
        if path.startswith("/chats/c1/messages?"):
            return await j(route, state["messages"])
        return await j(route, {"error": "unmocked " + path}, 404)
    if url.startswith("http://localhost:7860/"):
        return await route.fulfill(status=200, content_type="text/html", body=page_html)
    if url.startswith("https://storage.spicyapi.test/"):
        state["puts"].append({k: v for k, v in req.headers.items() if k in ("authorization", "content-type")})
        return await route.fulfill(status=200, body="", headers={"access-control-allow-origin": "*"})
    if url.startswith("https://cdn.spicyapi.test/") and url.endswith(".mp4"):
        return await route.fulfill(status=200, content_type="video/mp4", body=MP4, headers={"access-control-allow-origin": "*"})
    if url.startswith("https://cdn.spicyapi.test/"):
        return await route.fulfill(status=200, content_type="image/png", body=RESULT, headers={"access-control-allow-origin": "*"})
    if url.startswith("https://api.nano-gpt.com/"):
        if "/api/v1/models" in url:
            return await j(route, {"data": [{"id": "deepseek/x", "name": "DeepSeek X", "capabilities": {"vision": False, "structured_output": True}, "pricing": {"prompt": 0.2}},
                                            {"id": "openai/gpt-mini-vl", "name": "GPT mini", "capabilities": {"vision": True, "structured_output": True}, "pricing": {"prompt": 0.15}},
                                            {"id": "qwen/qwen3-vl", "name": "Qwen3 VL", "capabilities": {"vision": True}, "pricing": {"prompt": 0.3}},
                                            {"id": "gemini/flash", "name": "Gemini Flash", "capabilities": {"vision": True}}]})
        if url.endswith("/api/check-balance"):
            return await j(route, {"usd_balance": "7.5"} if req.headers.get("x-api-key") == "nano-test-key" else {"error": "bad key"}, 200 if req.headers.get("x-api-key") == "nano-test-key" else 401)
        if url.endswith("/api/v1/chat/completions"):
            if req.headers.get("authorization") != "Bearer nano-test-key": return await j(route, {"error": {"message": "bad nano key"}}, 401)
            state["log"].append("NANO chat " + json.loads(req.post_data)["model"])
            return await chat_reply(route, req)
    if url.startswith("https://api.spicyapi.ai/"):
        auth = req.headers.get("authorization")
        if "/console/v1/catalog/models" in url: return await j(route, {"data": {"models": [{k: v for k, v in m.items() if k != "inputSchema"} for m in MODELS]}})
        if auth != "Bearer spicy-test-key": return await j(route, {"error": {"message": "invalid api key"}}, 401)
        if url.startswith("https://api.spicyapi.ai/api/v1/models"): return await j(route, {"data": MODELS})
        if url.endswith("/api/v1/common/upload-url"):
            b = json.loads(req.post_data); state["log"].append("upload ticket %s %d bytes" % (b["contentType"], b["bytes"]))
            return await j(route, {"data": {"fileId": "f1", "uploadUrl": "https://storage.spicyapi.test/put/f1?sig=x", "method": "PUT",
                                            "headers": {"Content-Type": b["contentType"], "Content-Length": str(b["bytes"])}}})
        if "/api/v1/files/" in url and url.endswith("/commit"): return await j(route, {"data": {"status": "ready", "uri": "spicy://f/f1"}})
        if url.endswith("/api/v1/jobs/createTask"):
            b = json.loads(req.post_data); schema = SCHEMAS.get(b["model"], {"properties": {"prompt": {}}})
            unknown = [k for k in b["input"] if k not in schema["properties"]]
            state["inputs"].append({"model": b["model"], "input": {k: (v[:60] if isinstance(v, str) else v) for k, v in b["input"].items()}, "idem": bool(req.headers.get("idempotency-key"))})
            if unknown: return await j(route, {"error": {"message": "unknown field " + unknown[0]}}, 400)
            tid = "t%d" % len(state["inputs"]); state["tasks"][tid] = 0
            return await j(route, {"data": {"taskId": tid, "state": "queued"}}, 202)
        if "/api/v1/jobs/recordInfo" in url:
            tid = url.split("taskId=")[1]; state["tasks"][tid] += 1
            if state["tasks"][tid] < 2: return await j(route, {"data": {"taskId": tid, "state": "running"}})
            video = state["inputs"][int(tid[1:]) - 1]["model"].endswith("image-to-video")
            return await j(route, {"data": {"taskId": tid, "state": "succeeded", "cost": 0.08 if video else 0.036, "output": {"assets": [{"url": "https://cdn.spicyapi.test/%s.%s" % (tid, "mp4" if video else "png"), "mime": "video/mp4" if video else "image/png"}]}}})
        if url.endswith("/v1/chat/completions"):
            state["log"].append("SPICY chat " + json.loads(req.post_data)["model"])
            return await chat_reply(route, req)
        return await j(route, {"error": "unmocked spicy " + url}, 404)
    return await route.fulfill(status=599, body="blocked " + url)

async def chat_reply(route, req):
    if True:
        if True:
            b = json.loads(req.post_data); last = b["messages"][-1]["content"]; sysmsg = b["messages"][0]["content"] if b["messages"][0]["role"] == "system" else ""
            state["log"].append("chat " + b["model"])
            if isinstance(last, list):
                text = last[0]["text"]
                if "What color" in text: reply = '{"color":"red"}'
                elif "LEFT is the approved" in text: reply = '{"keys":["hair"]}'
                else: reply = '<think>x</think>{"face":"round face","eyes":"brown eyes","hair":"ash-brown wolf cut","skin":"fair","build":"slim"}'
            elif "Return JSON only: {\"ok\"" in sysmsg: reply = '{"ok":true,"scene":"apple on a sunny table"}'
            elif sysmsg.startswith("Invent one outfit"):
                reply = '{"outfit":"red satin slip dress, barefoot"}'
            elif sysmsg.startswith("It is morning") or sysmsg.startswith("It is night"):
                state["log"].append("DAILY writer: " + sysmsg[:40])
                reply = '{"scene":"Alex waking up in bed, messy sheets, morning sun","shot":"front-camera selfie","framing":"portrait","caption":"Morning ☀️ thinking of you","outfits":{"Alex":"oversized t-shirt"},"mood":{"level":5,"note":"cozy"}}'
            elif sysmsg.startswith("Plan a set of"):
                if "answers this dare" in sysmsg: state["log"].append("SET answers dare")
                n = int(sysmsg.split("Plan a set of ")[1].split(" ")[0]); state["log"].append("set plan n=%d tone has mood: %s" % (n, "Current mood: 8/10" in sysmsg))
                reply = json.dumps({"shots": [{"scene": "Alex in the hotel room, step %d" % (i + 1), "shot": "mirror selfie with the phone visible in the reflection"} for i in range(n)],
                                    "outfits": {"Alex": "black lace lingerie, heels"}, "mood": {"level": 9, "note": "very heated"}, "caption": "Dare accepted 😈"})
            elif sysmsg.startswith("Write the next photo"):
                state["log"].append("draft has style guide: %s | outfits in: %s" % ("phone" in sysmsg, json.loads(b["messages"][1]["content"])["currentOutfits"]))
                reply = '```json\n{"scene":"Alex at a candlelit bar, black lace dress, leaning in","shot":"flash selfie in a dim room","outfits":{"alex":"black lace dress, gold hoops"},"mood":{"level":8,"note":"teasing, heated"}}\n```'
            elif sysmsg.startswith("Write the next photo she sends") or sysmsg.startswith("Write the next picture"):
                state["log"].append("ANOTHER writer: has previous=%s" % ("previousPicture" in b["messages"][1]["content"]))
                reply = '{"scene":"Alex on the hotel bed, lace slipping off one shoulder","shot":"low-angle selfie","framing":"portrait","outfits":{"Alex":"black lace lingerie"},"mood":{"level":9,"note":"hot"}}'
            elif sysmsg.startswith("Write one or two sentences of motion"):
                reply = "She sways slowly toward the camera, biting her lip; the camera pushes in."
            elif "Decide if a new photo" in sysmsg or "Decide if the latest story beat" in sysmsg:
                conv = json.loads(b["messages"][1]["content"])["conversation"]
                state["log"].append("planner last turn: " + conv[-1]["text"][:30] + " | tone: " + sysmsg.split("Scene tone: ")[-1][:40])
                state["log"].append("planner roster outfit: %s | initiative rule: %s" % (json.loads(b["messages"][1]["content"])["roster"][0].get("currentOutfit"), "on her own" in sysmsg))
                mode = state["planner"]
                if mode == "nobody":
                    reply = json.dumps({"pictured": [], "mood": {"level": 4, "note": "calm"}})
                    return await j(route, {"choices": [{"message": {"content": reply}}]})
                if mode == "persona" and not state.get("prose_once"):
                    state["prose_once"] = True; state["log"].append("PLANNER answered in prose")
                    return await j(route, {"choices": [{"message": {"content": "<think>She wants {a photo"}}]})
                state["log"].append("PLANNER sees persona rule: %s | force: %s | narrator in convo: %s" % ("user’s own character takes a photo" in sysmsg, "you must choose who is visible" in sysmsg, '"role": "narrator"' in b["messages"][1]["content"]))
                reply = json.dumps({"pictured": ["ch1"], "scene": "Alex at a candlelit bar in a black lace dress", "shot": "mirror selfie", "unprompted": mode in ("photo", "persona"),
                                    "continues": mode == "continues", "dare": mode == "dare", "outfits": {"Alex": "black lace dress"}, "mood": {"level": 6, "note": "flirty"}})
                state["log"].append("PLANNER %s, saw localTime: %s" % (mode, "localTime" in b["messages"][1]["content"]))
            elif "You turn a decision into JSON" in sysmsg:
                state["log"].append("RETRY asked"); reply = json.dumps({"pictured": ["ch1"], "scene": "Alex laughing by the fire", "shot": "candid", "mood": {"level": 5}})
            else: reply = "Alex at a candlelit bar, black lace dress, leaning in with a sly smile."; state["log"].append("draft tone: " + sysmsg.split("Tone: ")[-1][:70])
            return await j(route, {"choices": [{"message": {"content": reply}}]})

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        page = await b.new_page(viewport={"width": 900, "height": 1500})
        await page.route("**/*", handle)
        await page.goto("http://localhost:7860/"); await page.wait_for_timeout(1200)
        out = lambda: page.locator("#chroma-likeness-panel output").inner_text()
        sel = lambda t: page.locator("#chroma-likeness-panel label", has_text=t).locator("select")
        inp = lambda t: page.locator("#chroma-likeness-panel label", has_text=t).locator("input")
        btn = lambda t: page.locator("#chroma-likeness-panel button", has_text=t)
        async def click(t, wait=1500):
            await btn(t).first.click(); await page.wait_for_timeout(wait)
        await page.click("#chroma-likeness-launch"); await page.wait_for_timeout(800)
        await inp("SpicyAPI key").fill("spicy-test-key"); await inp("NanoGPT key").fill("nano-test-key")
        await click("Save settings", 3000)
        await sel("Contextual photos work in").select_option("open")
        if "Enable" in await btn("contextual photos").first.inner_text(): await click("contextual photos", 1200)
        else: await page.wait_for_timeout(1200)
        print("BUTTON:", await btn("contextual photos").first.inner_text())
        # Switch Marinara to the roleplay chat and close the panel
        await page.evaluate("document.querySelector('[data-chat-composer]').dataset.chatId='c2'")
        await click("Close", 300)
        await page.wait_for_timeout(2500)
        state["planner"] = "persona"
        state["messages"] += [{"id": "u20", "role": "user", "content": "*I raise my phone and snap a photo of her as she laughs by the fire*", "createdAt": "2026-11-18T13:01"},
                              {"id": "n20", "role": "narrator", "content": "The flash catches her mid-laugh, firelight on her face.", "createdAt": "2026-11-18T13:02"}]
        toasts = []
        for _ in range(14):
            await page.wait_for_timeout(500)
            t = await page.evaluate("(() => { const t = document.querySelector('.chroma-likeness-toast'); return t && !t.hidden ? t.textContent : '' })()")
            if t and t not in toasts: toasts.append(t)
        print("TOASTS SEEN:", toasts)
        print("OUTPUT:", await page.evaluate("document.querySelector('#chroma-likeness-panel output').textContent"))
        print("LOG:", state["log"][-8:])
        print("ERRORS so far:", await page.evaluate("__errors"))
        toast = page.locator(".chroma-likeness-toast")
        print("TOAST:", await toast.inner_text() if await toast.is_visible() else "(none visible)")
        posted = [l for l in state["log"] if l.startswith("POSTED")]
        print("POSTED after persona photo:", posted[-1] if posted else "nothing")
        print("PROMPT ratio:", state["inputs"][-1]["input"].get("aspect_ratio") if state["inputs"] else None)
        # Force button when the writer cannot pick anyone
        await page.click("#chroma-likeness-launch"); await page.wait_for_timeout(1500)
        await page.wait_for_timeout(2500)
        state["planner"] = "nobody"
        await click("Picture the last reply", 2500); print("FORCE (nobody):", await out())
        state["planner"] = "dare_off"
        await click("Picture the last reply", 4000); print("FORCE:", await out())
        print("PLANNER LOG:", [l for l in state["log"] if l.startswith("PLANNER")])
        print("ERRORS:", await page.evaluate("__errors"))
        print("VIEW RELOADS:", await page.evaluate("__inval"))
        await b.close()
asyncio.run(main())
