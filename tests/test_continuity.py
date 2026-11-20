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
window.marinara = {{ fetch: (...a) => window.fetch(...a), onCleanup(){{}}, storage: {{ get: () => fetch('/__storage').then(r => r.json()), patch: (v) => fetch('/__storage', {{method: 'POST', body: JSON.stringify(v)}}).then(r => r.json()) }}, setInterval: (f,t)=>setInterval(f,Math.min(t,1500)),
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
state0 = {"char": {"name": "Alex", "extensions": {"imageAppearance": "Original look from the card", "imageAppearanceEnabled": True}},
         "gallery": [], "tasks": {}, "log": [], "inputs": [], "puts": [], "planner": "photo",
         "messages": [
                {"id": "m3", "role": "assistant", "characterId": "ch1", "content": "*laughs* Fine, here's one from the bar. Black lace, just for you.", "createdAt": "2026-11-18T10:03"},
                {"id": "m1", "role": "user", "content": "How's the party?", "createdAt": "2026-11-18T10:01"},
                {"id": "m2", "role": "user", "content": "Send me a pic of what you're wearing tonight?", "createdAt": "2026-11-18T10:02"}]}
state = dict(state0, msgs={"c1": state0["messages"], "c2": []}, galleries={"c1": [], "c2": []}, meta={"c1": {}, "c2": {}}, storage={}, planner="none")
def merge(a, b):
    for k, v in b.items():
        if v is None: a.pop(k, None)
        elif isinstance(v, dict) and isinstance(a.get(k), dict): merge(a[k], v)
        else: a[k] = v
    return a
def j(route, data, status=200):
    return route.fulfill(status=status, content_type="application/json", body=json.dumps(data), headers={"access-control-allow-origin": "*"})

async def handle(route):
    if route.request.url.startswith("https://api.runware.ai/v1"):
        body = json.loads(route.request.post_data or "[]")
        state["runware_auth"] = route.request.headers.get("authorization", "")
        task = body[0] if body else {}
        if task.get("taskType") == "authentication":
            return await route.fulfill(status=200, content_type="application/json", body=json.dumps({"data": [{"taskType": "authentication", "connectionSessionUUID": "s1"}]}))
        refs = len((task.get("inputs") or {}).get("referenceImages") or [])
        state["log"].append("RUNWARE model=%s refs=%d size=%s neg=%s" % (task.get("model"), refs, "%sx%s" % (task.get("width"), task.get("height")) if "width" in task else "none", "negativePrompt" in task))
        if refs and "width" in task:
            return await route.fulfill(status=400, content_type="application/json", body=json.dumps({"errors": [{"code": "unsupportedParameter", "message": "width and height cannot be used together with referenceImages", "parameter": "width", "taskUUID": task.get("taskUUID")}]}))
        return await route.fulfill(status=200, content_type="application/json", body=json.dumps({"data": [{"taskType": "imageInference", "taskUUID": task.get("taskUUID"), "imageUUID": "u1", "imageDataURI": "data:image/png;base64," + base64.b64encode(RESULT).decode(), "cost": 0.03}]}))
    req, url = route.request, route.request.url
    if url.startswith("http://localhost:7860/__storage"):
        if req.method == "POST":
            body = json.loads(req.post_data)
            for k, v in body.items():
                if v is None: state["storage"].pop(k, None)
                else: state["storage"][k] = v
            state["log"].append("STORAGE " + ",".join(sorted(body.keys())))
        return await j(route, state["storage"])
    if url.startswith("http://localhost:7860/api/"):
        path = url[len("http://localhost:7860/api"):]
        if path == "/chats": return await j(route, [{"id": "c1", "name": "DM chat", "characterIds": '["ch1"]', "mode": "conversation"}, {"id": "c2", "name": "Story", "characterIds": '["ch1"]', "mode": "roleplay"}])
        m = re.match(r"^/chats/(c\d)$", path)
        if m: return await j(route, {"id": m.group(1), "characterIds": '["ch1"]', "mode": "conversation" if m.group(1) == "c1" else "roleplay", "connectionId": "n1", "metadata": json.dumps(state["meta"][m.group(1)])})
        cm = re.match(r"^/(?:chats|gallery)/(c\d)", path)
        cid = cm.group(1) if cm else "c1"
        msgs, gal = state["msgs"][cid], state["galleries"][cid]
        path = re.sub(r"/(chats|gallery)/c\d", r"/\1/c1", path)
        if path == "/connections": return await j(route, [
            {"id": "s1", "name": "SpicyAPI images", "provider": "image_generation", "model": "bytedance/seedream-5.0-pro/edit", "baseUrl": "https://api.spicyapi.ai/api/v1"},
            {"id": "n1", "name": "NanoGPT chat", "provider": "nanogpt", "model": "deepseek/x", "baseUrl": "https://nano-gpt.com/api/v1"}])
        if path == "/characters/ch1/gallery/upload" and req.method == "POST":
            state["log"].append("CHAR GALLERY upload")
            return await j(route, {"id": "cg%d" % len(state["log"]), "filename": "x.png"})
        if path == "/characters/ch1":
            if req.method == "PATCH":
                body = json.loads(req.post_data); merge(state["char"], body["data"]); state["log"].append("PATCH card " + ",".join(body["data"].get("extensions", {}).keys()))
            return await j(route, {"id": "ch1", "data": json.dumps({"data": state["char"]})})
        if path == "/gallery/c1/upload":
            gid = "g%d" % (len(gal) + 100 * (cid == "c2") + 2)
            raw = req.post_data_buffer or b""
            ext = "mp4" if b"likeness.mp4" in raw else "jpg" if b"likeness.jpeg" in raw else "png"
            state["log"].append("upload " + ext)
            item = {"id": gid, "url": "/api/gallery/file/%s/%s.%s" % (cid, gid, ext), "chatId": cid, "provider": "chroma-likeness", "model": "m", "prompt": "p", "createdAt": "2026-11-18T10:%02d" % (len(gal) % 60)}
            gal.insert(0, item); return await j(route, item)
        if path.startswith("/gallery/file/"):
            return await route.fulfill(status=200, content_type="image/png", body=PORTRAIT)
        if path == "/gallery/c1": return await j(route, gal)
        if path.startswith("/chats/c1/messages/") and path.endswith("/extra") and req.method == "PATCH":
            mid = path.split("/")[4]; b = json.loads(req.post_data)
            for m in msgs:
                if m["id"] == mid:
                    ex = json.loads(m.get("extra") or "{}") if isinstance(m.get("extra"), str) or not m.get("extra") else m["extra"]
                    ex.update(b); m["extra"] = json.dumps(ex)
                    state["log"].append("ATTACHED in %s to %s (%s) %s" % (cid, mid, m["role"], [x["url"].rsplit("/",1)[-1] for x in ex.get("attachments", [])]))
                    return await j(route, m)
            return await j(route, {"error": "no message"}, 404)
        if path == "/chats/c1/messages":
            b = json.loads(req.post_data); ex = b["extra"]
            if b["role"] == "user":
                state["log"].append("USER MESSAGE " + b["content"]); return await j(route, {"id": "u"})
            if b.get("content"): state["log"].append("WITH TEXT «" + b["content"][:50] + "»")
            n = len(msgs) + 10
            msgs.append({"id": "p%d" % n, "role": "assistant", "characterId": "ch1", "content": b.get("content", ""), "extra": json.dumps(ex), "createdAt": "2026-11-18T11:%02d" % (n % 60)})
            state["log"].append(cid + " POSTED %s%s%s" % ([a["type"] + ":" + a["url"].rsplit("/", 1)[-1] + " «" + str(a.get("prompt"))[:45] + "»" for a in ex["attachments"]], " LOCKED" if ex.get("likenessLocked") else "", " UNLOCK" if ex.get("likenessUnlocked") else ""))
            return await j(route, {"id": "m"})
        if path.startswith("/chats/c1/messages?"):
            return await j(route, msgs)
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
            state["inputs"].append({"model": b["model"], "input": {k: (v[:60] if isinstance(v, str) else v) for k, v in b["input"].items()}, "idem": bool(req.headers.get("idempotency-key")), "full": b["input"].get("prompt", "")})
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
                elif "of the outfit" in text:
                    state["log"].append("OUTFIT VISION two=%s rated=%s" % ("LEFT is the approved picture of the outfit" in text, "POOR" if "POOR" in text else "GOOD"))
                    reply = json.dumps({"description": "floor-length deep red silk gown, deep V neckline, thigh-high slit on the left leg, thin spaghetti straps, open back, gold strappy heels, gold cuff bracelet, gold drop earrings", "note": "the slit is on the left leg and reaches the thigh"})
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
                roster = json.loads(b["messages"][1]["content"])["roster"]
                state["log"].append("PLANNER %s sees outfit=%s wardrobe=%s closetRule=%s" % (mode, roster[0].get("currentOutfit"), roster[0].get("wardrobe"), "wardrobeAdd" in sysmsg))
                extra = {"wardrobe": {"pictured": [], "wardrobeAdd": [{"name": "Alex", "title": "Red silk gown", "outfit": "floor-length red silk gown with a deep V neckline and thigh-high slit, thin straps, gold strappy heels, gold cuff bracelet and drop earrings"}]},
                         "beat": {"pictured": ["ch1"], "scene": "Alex stepping onto the moonlit dock of the lake house", "shot": "wide", "unprompted": True},
                         "wear": {"pictured": ["ch1"], "scene": "Alex turning by the fire to show off the gown", "shot": "full body", "wear": {"Alex": "red silk gown"}},
                         "again": {"pictured": ["ch1"], "scene": "Alex leaning on the balcony rail", "shot": "medium"},
                         "quiet": {"pictured": []},
                         "selfie": {"pictured": ["ch1"], "scene": "Alex mirror selfie in the red silk gown", "shot": "mirror selfie", "caption": "Alex in the red silk gown in her bedroom mirror", "why": "you asked to see the dress on her", "text": "Here it is on 😘 what do you think?"}}.get(mode)
                if mode == "npc":
                    taken, insist = "A photo is being taken" in sysmsg, "you must choose who is visible" in sysmsg
                    state["log"].append("NPC PLAN taken-rule=%s insist=%s" % (taken, insist))
                    extra = {"pictured": ["ch1"], "scene": "Alex mid-laugh on the bridge, caught by Marco's camera", "shot": "candid phone photo", "unprompted": True} if insist else {"pictured": []}
                if extra is not None:
                    return await j(route, {"choices": [{"message": {"content": json.dumps({**extra, "mood": {"level": 6, "note": "warm"}})}}]})
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

from datetime import datetime, timezone
def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
def closet(): return {k: v for k, v in state["char"].get("extensions", {}).get("chromaLikenessCloset", {}).items() if v}
async def toasts(page, seconds):
    seen = []
    for _ in range(int(seconds * 10)):
        await page.wait_for_timeout(100)
        t = await page.evaluate("(() => { const t = document.querySelector('.chroma-likeness-toast'); return t && !t.hidden ? t.textContent : '' })()")
        if t and t not in seen: seen.append(t)
    return seen
async def open_page(b):
    ctx = await b.new_context(viewport={"width": 900, "height": 1500})   # a fresh browser profile: empty browser storage
    page = await ctx.new_page(); await page.route("**/*", handle)
    await page.goto("http://localhost:7860/"); await page.wait_for_timeout(1500)
    return ctx, page
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        # 1. Keys typed on one device are saved in Marinara
        ctx, page = await open_page(b)
        L = lambda sel, t: page.locator("#chroma-likeness-panel " + sel, has_text=t)
        await page.click("#chroma-likeness-launch"); await page.wait_for_timeout(800)
        await L("label", "API key for the picture provider").locator("input").fill("spicy-test-key"); await L("label", "NanoGPT key").locator("input").fill("nano-test-key")
        await L("button", "Save settings").first.click(); await page.wait_for_timeout(3000)
        cfg = state["storage"].get("config", {})
        print("1 STORED IN MARINARA:", {k: cfg.get(k) for k in ("spicyKey", "nanoKey")}, "| auto-watch button:", await L("button", "contextual photos").first.inner_text())
        await ctx.close()
        # 2. A different browser (nothing stored locally) gets the keys back from Marinara and starts watching
        state["storage"]["state/c1"] = {"outfits": {"ch1": "black satin slip dress, strappy heels"}, "mood": {"level": 6, "note": "flirty"}}
        ctx, page = await open_page(b)
        L = lambda sel, t: page.locator("#chroma-likeness-panel " + sel, has_text=t)
        await page.click("#chroma-likeness-launch"); await page.wait_for_timeout(1500)
        print("2 FRESH BROWSER key field:", await L("label", "API key for the picture provider").locator("input").input_value(), "| button:", await L("button", "contextual photos").first.inner_text())
        print("2 STATUS:", (await page.locator("#chroma-likeness-panel small", has_text="Status:").first.inner_text()).replace("\n", " || "))
        await page.evaluate("document.querySelectorAll('#chroma-likeness-panel details').forEach(d => d.open = true)")
        state["storage"]["config"]["heat"] = "explicit"
        await L("button", "Reload settings from Marinara").first.click(); await page.wait_for_timeout(1500)
        print("2 RELOAD heat:", await L("label", "Heat").locator("select").input_value() if await L("label", "Heat").count() else "(no heat select)")
        # Heart a picture so later pictures are edits of the likeness
        await page.locator("#chroma-likeness-panel label", has_text="Scene or image prompt").locator("textarea").fill("Alex at a beach cafe, sunset")
        await L("button", "Generate and post").first.click(); await page.wait_for_timeout(3000)
        await page.locator("#chroma-likeness-panel .person-tile").first.click(); await page.wait_for_timeout(1500)
        await page.locator("#chroma-likeness-wardrobe button", has_text="♡").first.click(); await page.wait_for_timeout(2500)
        await page.locator("#chroma-likeness-wardrobe header button", has_text="Close").first.click(); await page.wait_for_timeout(300)
        print("2 HEART:", (await page.evaluate("document.querySelector('#chroma-likeness-panel output').textContent"))[:120])
        await L("button", "Close").first.click(); await page.wait_for_timeout(300)
        # 3. "Add the red gown to your wardrobe" in Chat
        state["planner"] = "wardrobe"
        state["msgs"]["c1"] += [{"id": "u31", "role": "user", "content": "That red silk gown is stunning. Add it to your wardrobe.", "createdAt": now()},
                                {"id": "a31", "role": "assistant", "characterId": "ch1", "content": "Done, it's yours to see again whenever you like.", "createdAt": now()}]
        print("3 WARDROBE toasts:", await toasts(page, 5))
        print("3 CLOSET:", [(v.get("title"), len(v["outfit"]), v.get("auto")) for v in closet().values()])
        # 3b. A photo asked for in Chat arrives with her message, and its description and reason
        state["planner"] = "selfie"
        state["msgs"]["c1"] += [{"id": "u32", "role": "user", "content": "Send me a pic of you wearing it?", "createdAt": now()},
                                {"id": "a32", "role": "assistant", "characterId": "ch1", "content": "One sec, changing into it now...", "createdAt": now()}]
        await toasts(page, 6)
        post = [m for m in state["msgs"]["c1"] if m["id"].startswith("p")][-1]
        ex = json.loads(post["extra"])
        print("3b CHAT PHOTO: message text =", repr(post["content"]), "| photo note =", ex["attachments"][0].get("prompt"))
        print("3b CHARACTER GALLERY uploads so far:", len([l for l in state["log"] if l == "CHAR GALLERY upload"]))
        # 4. Marinara builds a scene from the Chat: a new Roleplay chat linked to c1, opened with a fresh reply
        state["meta"]["c2"] = {"sceneOriginChatId": "c1", "sceneStatus": "active"}
        state["msgs"]["c2"] += [{"id": "n40", "role": "narrator", "content": "The lake house glows as you both arrive; she steps onto the dock.", "createdAt": now()}]
        state["planner"] = "beat"
        await page.evaluate("document.querySelector('[data-chat-composer]').dataset.chatId='c2'")
        print("4 SCENE toasts:", await toasts(page, 7))
        print("4 CARRIED:", state["storage"].get("state/c2", {}).get("outfits"), "| link:", state["storage"].get("link/c2", {}).get("origin"))
        print("4 FIRST REPLY PICTURED:", [l for l in state["log"] if l.startswith("ATTACHED in c2")])
        # 5. Wear the saved gown in the scene; the next picture uses the gown's photo for the clothes
        state["planner"] = "wear"
        state["msgs"]["c2"] += [{"id": "u41", "role": "user", "content": "Put on your red silk gown for me.", "createdAt": now()},
                                {"id": "n41", "role": "narrator", "content": "She returns in the red gown, turning slowly by the fire.", "createdAt": now()}]
        print("5 WEAR toasts:", await toasts(page, 7))
        print("5 OUTFIT NOW:", state["storage"].get("state/c2", {}).get("outfits", {}).get("ch1", "")[:60], "| closet pictures:", [bool(v.get("picture")) for v in closet().values() if v.get("title")])
        state["planner"] = "again"
        state["msgs"]["c2"] += [{"id": "u42", "role": "user", "content": "*I snap a photo of you on the balcony*", "createdAt": now()},
                                {"id": "n42", "role": "narrator", "content": "She leans on the rail, the gown catching the moonlight.", "createdAt": now()}]
        await toasts(page, 7)
        last = state["inputs"][-1]["input"]
        print("5 OUTFIT REFERENCE: images=%d outfit-note=%s" % (len(last.get("image_urls", [])), "Image 2 shows the outfit" in last.get("prompt", "")))
        # 5c. The Wardrobe: thumbnails, the outfit folder, rating a photo of the outfit
        await page.click("#chroma-likeness-launch"); await page.wait_for_timeout(1200)
        await page.evaluate("document.querySelectorAll('#chroma-likeness-panel details').forEach(d => d.open = true)")
        await page.wait_for_timeout(1500)
        await page.locator("#chroma-likeness-panel .person-tile").first.click(); await page.wait_for_timeout(2000)
        tiles = page.locator("#chroma-likeness-wardrobe .wardrobe .outfit-tile")
        print("5c TILES:", await tiles.count(), [await tiles.nth(i).inner_text() for i in range(await tiles.count())][:3], "| thumbnail:", await tiles.first.locator("img").count())
        await tiles.filter(has_text="Red silk gown").first.click(); await page.wait_for_timeout(1500)
        box = page.locator("#chroma-likeness-wardrobe")
        print("5c BACK button:", await box.locator("header button", has_text="← Alex").count())
        print("5c FOLDER open:", await box.evaluate("d => d.open"), "| photos:", await box.locator("figure").count(), "| ref:", await box.locator("img.outfit-ref").count())
        await box.locator("figure").first.locator("button", has_text="👎").click(); await page.wait_for_timeout(2500)
        await page.set_viewport_size({"width": 420, "height": 900}); await page.wait_for_timeout(300); await page.screenshot(path="/tmp/folder.png"); await page.set_viewport_size({"width": 900, "height": 1500})
        print("5c RATE:", await box.locator("output").inner_text())
        print("5c LEARNED:", [l for l in state["log"] if l.startswith("OUTFIT VISION")], "| notes:", await box.locator(".outfit-notes li").count(), "| undo:", await box.locator("button", has_text="Undo last change").count())
        gown = [v for v in closet().values() if v.get("title") == "Red silk gown"][0]
        print("5c CARD:", gown["outfit"][:50], "| notes:", gown.get("notes"), "| votes:", list(gown.get("votes", {}).values()))
        await box.locator("button", has_text="Undo last change").click(); await page.wait_for_timeout(1500)
        print("5c UNDO:", [v for v in closet().values() if v.get("title") == "Red silk gown"][0]["outfit"][:40])
        await box.locator("button", has_text="Close").first.click(); await page.wait_for_timeout(300)
        await page.locator("#chroma-likeness-panel button", has_text="Close").first.click(); await page.wait_for_timeout(300)
        # 5d. Redo a picture with an edited prompt; it replaces the old one in its message
        await page.click("#chroma-likeness-launch"); await page.wait_for_timeout(1200)
        await page.locator("#chroma-likeness-panel .person-tile").first.click(); await page.wait_for_timeout(2000)
        n_att = len([l for l in state["log"] if l.startswith("ATTACHED")])
        await box.locator("article button", has_text="✎").first.click(); await page.wait_for_timeout(800)
        print("5d REDO view:", await box.locator("h2").inner_text(), "| prompt:", (await box.locator("textarea").input_value())[:60])
        await box.locator("textarea").fill("Alex laughing on the balcony, wind in the red silk gown")
        await box.locator("button", has_text="Redo").click(); await page.wait_for_timeout(4000)
        print("5d REDO:", await box.locator("output").inner_text(), "|", [l for l in state["log"] if l.startswith("ATTACHED")][n_att:][:1])
        await box.locator("button", has_text="← Alex").click(); await page.wait_for_timeout(1500)
        before = len([l for l in state["log"] if l == "CHAR GALLERY upload"])
        await box.locator("button", has_text="Add this character").click(); await page.wait_for_timeout(4000)
        print("5d COPY TO GALLERY:", await box.locator("output").inner_text(), "| new uploads:", len([l for l in state["log"] if l == "CHAR GALLERY upload"]) - before)
        await box.locator("header button", has_text="Close").first.click(); await page.wait_for_timeout(300)
        await page.locator("#chroma-likeness-panel button", has_text="Close").first.click(); await page.wait_for_timeout(300)
        # 5b. A side character takes the photo, right after another picture
        state["planner"] = "npc"
        state["msgs"]["c2"] += [{"id": "u43", "role": "user", "content": "We walk out onto the old stone bridge.", "createdAt": now()},
                                {"id": "n43", "role": "narrator", "content": "Marco, the street photographer, grins and snaps a picture of her as she laughs.", "createdAt": now()}]
        await toasts(page, 8)
        npc_prompt = state["inputs"][-1]["full"]
        print("5b LEARNED NOTE IN NEXT PICTURE:", "Get these right: the slit is on the left leg" in npc_prompt, "| images:", len(state["inputs"][-1]["input"].get("image_urls", [])))
        print("5b NPC PHOTO:", [l for l in state["log"] if l.startswith("NPC PLAN")], [l for l in state["log"] if l.startswith("ATTACHED in c2 to n43")])
        # 6. End scene: Marinara clears the link and writes a recap into the Chat; back in the Chat
        state["meta"]["c2"] = {}
        state["msgs"]["c1"] += [{"id": "r50", "role": "system", "content": "Scene recap: an evening at the lake house.", "extra": json.dumps({"sceneChatId": "c2"}), "createdAt": now()}]
        state["planner"] = "quiet"
        await page.evaluate("document.querySelector('[data-chat-composer]').dataset.chatId='c1'")
        print("6 RETURN toasts:", await toasts(page, 7))
        print("6 PHOTO IN CHAT:", [l for l in state["log"] if l.startswith("c1 POSTED")][-1:])
        print("6 OUTFIT BACK IN CHAT:", state["storage"].get("state/c1", {}).get("outfits", {}).get("ch1", "")[:40])
        # 8. Runware as the picture provider: paired keys, its models and limits, a real request
        await page.click("#chroma-likeness-launch"); await page.wait_for_timeout(1000)
        await page.evaluate("document.querySelectorAll('#chroma-likeness-panel details').forEach(d => d.open = true)")
        prov = page.locator("#chroma-likeness-panel label", has_text="Picture provider").locator("select")
        key = page.locator("#chroma-likeness-panel label", has_text="API key for the picture provider").locator("input")
        await prov.select_option("runware"); await page.wait_for_timeout(300)
        print("8 KEY BOX on Runware:", repr(await key.input_value()), "| placeholder:", await key.get_attribute("placeholder"))
        await key.fill("rw-test-key")
        await prov.select_option("spicyapi"); await page.wait_for_timeout(200)
        print("8 KEY BOX back on SpicyAPI:", await key.input_value())
        await prov.select_option("runware"); await page.wait_for_timeout(300)
        print("8 KEY BOX on Runware again:", await key.input_value())
        edit_sel = page.locator("#chroma-likeness-panel .model-picker", has_text="Hearted pictures").locator("select")
        print("8 EDIT MODEL:", await edit_sel.input_value(), "| hint:", (await page.locator("#chroma-likeness-panel .model-picker", has_text="Hearted pictures").locator("small").inner_text())[:110])
        print("8 GEN OPTIONS:", [o for o in await page.locator("#chroma-likeness-panel .model-picker", has_text="New pictures").locator("option").all_inner_texts()][:4])
        await page.locator("#chroma-likeness-panel button", has_text="Save settings").first.click(); await page.wait_for_timeout(1500)
        cfg = state["storage"].get("config", {})
        print("8 SAVED:", {k: cfg.get(k) for k in ("imageProvider", "spicyKey", "runwareKey")}, "| runware models:", cfg.get("runwareModels"))
        await page.locator("#chroma-likeness-panel button", has_text="Check connection").first.click(); await page.wait_for_timeout(2500)
        print("8 CHECK:", [l for l in (await page.evaluate("document.querySelector('#chroma-likeness-panel output').textContent")).split("\n") if "Runware" in l], "| auth header:", state.get("runware_auth"))
        await page.locator("#chroma-likeness-panel label", has_text="Scene or image prompt").locator("textarea").fill("Alex on a rooftop at dusk")
        await page.locator("#chroma-likeness-panel button", has_text="Generate and post").first.click(); await page.wait_for_timeout(4000)
        print("8 RUNWARE REQUESTS:", [l for l in state["log"] if l.startswith("RUNWARE")])
        print("8 POSTED:", [l for l in state["log"] if "POSTED" in l][-1:])
        await page.locator("#chroma-likeness-panel button", has_text="Close").first.click(); await page.wait_for_timeout(300)
        # 7. Status line for the chat selected in the panel
        await page.click("#chroma-likeness-launch"); await page.wait_for_timeout(1500)
        await page.set_viewport_size({"width": 420, "height": 900}); await page.wait_for_timeout(300)
        await page.screenshot(path="/tmp/panel_phone.png")
        await page.locator("#chroma-likeness-panel .person-tile").first.click(); await page.wait_for_timeout(2000)
        await page.screenshot(path="/tmp/person.png")
        await page.locator("#chroma-likeness-wardrobe").evaluate("d => d.scrollTop = d.scrollHeight * 0.55"); await page.wait_for_timeout(300)
        await page.screenshot(path="/tmp/person2.png")
        await page.locator("#chroma-likeness-wardrobe header button", has_text="Close").first.click(); await page.wait_for_timeout(300)
        await page.set_viewport_size({"width": 900, "height": 1500})
        print("7 STATUS:", (await page.locator("#chroma-likeness-panel small", has_text="Status:").first.inner_text()).replace("\n", " || "))
        print("PLANNER LOG:", [l for l in state["log"] if l.startswith("PLANNER")])
        print("ERRORS:", await page.evaluate("__errors"))
        await page.screenshot(path=OUT, full_page=True)
        await b.close()
asyncio.run(main())
