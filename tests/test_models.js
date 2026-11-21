// SpicyAPI model recognition without a browser: new kinds of model id, close matches, direct lookup.
// Run: node tests/test_models.js "extension/Chroma Likeness/extension.js"
const fs = require("fs");
const s = fs.readFileSync(process.argv[2], "utf8");
const grab = (n) => { const i = s.indexOf(n); const j = s.indexOf("\n}\n", i); return s.slice(i, j + 3); };
let fails = 0;
const check = (name, ok, extra = "") => { console.log((ok ? "✓ " : "✗ FAIL ") + name + (extra ? " | " + extra : "")); if (!ok) fails++; };
const env = `
const catalog = { meta: new Map(), schemas: new Map(), live: new Set() };
const enc = encodeURIComponent; const logs = []; function logStep(m){logs.push(m)} function spicyKey(){return "k"}
function unwrap(j){return j&&j.data!==undefined&&!Array.isArray(j)?j.data:j}
function num(x){return typeof x==="number"?x:undefined}
async function spicy(path){ if(path.includes("acme%2Fnewpic")||path.includes("acme/newpic/image-to-image")) return {json:async()=>({data:{id:"acme/newpic/image-to-image",inputSchema:{properties:{prompt:{type:"string"},image_url:{type:"string"}},required:["prompt","image_url"]}}})}; throw Error("404 not found"); }
`;
eval(env + grab("function addModel") + grab("function closeModels") + grab("async function lookUpModel") + grab("function unknownModelText") +
  ";globalThis.A=addModel;globalThis.CM=closeModels;globalThis.L=lookUpModel;globalThis.U=unknownModelText;globalThis.CAT=catalog;globalThis.LOGS=logs;");
(async () => {
  A({ id: "bytedance/seedream-5.0-pro/edit", modality: "image", inputSchema: { properties: { prompt: {}, image_urls: { type: "array", maxItems: 10 } } } });
  A({ id: "acme/flash/image-to-image", inputSchema: { properties: { prompt: { type: "string" }, image: { type: "string" }, seed: {} }, required: ["prompt", "image"] } });
  A({ id: "acme/flash/generate", inputSchema: { properties: { prompt: { type: "string" }, width: {}, height: {} } } });
  A({ id: "acme/mystery" });
  A({ id: "some/llm", modality: "text" });
  const m = (id) => CAT.meta.get(id) || {};
  check("image-to-image id is an editing model", m("acme/flash/image-to-image").edit === true && m("acme/flash/image-to-image").gen === false);
  check("schema with prompt and size is a generation model", m("acme/flash/generate").image === true && m("acme/flash/generate").gen === true && !m("acme/flash/generate").edit);
  check("unclear model still counts as listed", CAT.meta.has("acme/mystery") && m("acme/mystery").unsure === true);
  check("text model stays text", m("some/llm").text === true && !m("some/llm").image);
  check("seedream edit unchanged", m("bytedance/seedream-5.0-pro/edit").edit === true && m("bytedance/seedream-5.0-pro/edit").maxInputs === 10);
  const near = CM("seedream-5.0-pro", "edit");
  check("short id suggests the full id", near[0] === "bytedance/seedream-5.0-pro/edit", near.join(","));
  check("unknown text names the closest id", U("Seedream 5.0 Pro", "edit").includes("bytedance/seedream-5.0-pro/edit"));
  const found = await L("acme/newpic/image-to-image");
  check("direct lookup adds a model missing from the list", found && found.edit === true);
  const missing = await L("nope/nothing");
  check("unknown id stays unknown and is logged", !missing && LOGS.some((l) => /does not recognise/.test(l)));
  console.log(fails ? fails + " FAILED" : "ALL PASSED");
  process.exit(fails ? 1 : 0);
})();
