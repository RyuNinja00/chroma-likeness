// Prompt and reference-picture rules without a browser.
// Run: node tests/test_prompts.js "extension/Chroma Likeness/extension.js"
const fs = require("fs");
const s = fs.readFileSync(process.argv[2], "utf8");
const grab = (n) => { const i = s.indexOf(n); const j = s.indexOf("\n}\n", i); return s.slice(i, j + 3); };
const line = (n) => { const i = s.indexOf(n); return s.slice(i, s.indexOf("\n", i) + 1); };
let sent = null, fails = 0;
const check = (name, ok, extra = "") => { console.log((ok ? "✓ " : "✗ FAIL ") + name + (extra ? " | " + extra : "")); if (!ok) fails++; };
// Fake SpicyAPI catalogue: input rules for four kinds of editing model.
const catalog = { meta: new Map(), schemas: new Map() };
catalog.meta.set("seedream", { edit: true, maxInputs: 10, maxPrompt: 1500 });
catalog.schemas.set("seedream", { properties: { prompt: { type: "string", maxLength: 1500 }, image_urls: { type: "array", maxItems: 10 } } });
catalog.meta.set("single", { edit: true });
catalog.schemas.set("single", { properties: { prompt: { type: "string" }, image_url: { type: "string" } } });
catalog.meta.set("listnocap", { edit: true });
catalog.schemas.set("listnocap", { properties: { prompt: { type: "string" }, images: { type: "array" } } });
catalog.meta.set("unknown", { edit: true });
catalog.meta.set("three", { edit: true });
catalog.schemas.set("three", { properties: { prompt: { type: "string" }, image_urls: { type: "array", maxItems: 3 } } });
const env = `
const adultAnchor="All people shown are adults.";
function modelMeta(m){return catalog.meta.get(m)} function savedModel(){return "seedream"} function imageKey(){return "k"} function wantsTags(){return false}
function withoutSelfieNote(x){return x}
async function modelSchema(){}
async function spicyImage(prompt,model,ratio,w,h,refs){sent={prompt,refs};return {blob:new Blob([new Uint8Array([137,80,78,71,0,0,0,0,0,0,0,0])],{type:"image/png"}),cost:0}}
`;
eval(env + line("const hairWear") + line("const identityWords") + grab("function referenceEditPrompt") + grab("function refCapacity") + grab("function soloPlan") + grab("function capacityText") +
  grab("async function render(") + grab("async function outfitReference") + ";globalThis.R=render;globalThis.E=referenceEditPrompt;globalThis.O=outfitReference;globalThis.C=capacityText;globalThis.K=refCapacity;");
const pic = (t) => new Blob([t]);
const tag = (b) => b && b.size ? b.text() : "";
(async () => {
  // Hair accessories survive, hair colour and haircut words do not.
  const e = E("She wears a red silk gown, a gold clip in her blonde hair, a wolf cut, green eyes, a ribbon in her hair", "");
  check("hair accessories kept", e.includes("gold clip in her hair") && e.includes("ribbon in her hair") && !/blonde|wolf cut|green eyes/.test(e.slice(e.indexOf("Scene changes"))));

  // Model limits, as shown in Settings.
  check("seedream limit", K("seedream").max === 10 && K("seedream").stated, C("seedream"));
  check("single-picture model", K("single").max === 1, C("single"));
  check("list without a stated limit plays safe", K("listnocap").max === 2 && !K("listnocap").stated, C("listnocap"));
  check("rules not loaded plays safe", K("unknown").max === 1 && !K("unknown").stated, C("unknown"));

  // One person: main heart + 2 extra hearts + outfit fit a 10-picture model, in a fixed order.
  const outfit = { blob: pic("outfit"), title: "Red silk gown", notes: ["slit on the left leg"] };
  let r = await R("Alex at the gala", pic("main"), "3:4", undefined, "seedream", "", null, false, "", outfit, [pic("x1"), pic("x2")]);
  const order = await Promise.all(sent.refs.map(tag));
  check("10-picture model sends main, extra, extra, outfit", JSON.stringify(order) === JSON.stringify(["main", "x1", "x2", "outfit"]) && r.refsSent === 4, order.join(","));
  check("prompt names the extra hearts and the outfit image", sent.prompt.includes("Images 1 to 3 all show the same person") && sent.prompt.includes("Image 4 shows the outfit"));

  // A 3-picture model: main + 1 extra + outfit (2nd extra skipped).
  await R("Alex at the gala", pic("main"), "3:4", undefined, "three", "", null, false, "", outfit, [pic("x1"), pic("x2")]);
  check("3-picture model sends main, extra, outfit", JSON.stringify(await Promise.all(sent.refs.map(tag))) === JSON.stringify(["main", "x1", "outfit"]) && sent.prompt.includes("Image 3 shows the outfit"));

  // A list model with no stated limit: 2 pictures, main + 1 extra.
  await R("Alex at the gala", pic("main"), "3:4", undefined, "listnocap", "", null, false, "", outfit, [pic("x1"), pic("x2")]);
  check("unstated list limit sends 2", sent.refs.length === 2 && !sent.prompt.includes("shows the outfit"));

  // A single-picture model never gets more than the main heart, and two-person pictures are refused.
  await R("Alex at the gala", pic("main"), "3:4", undefined, "single", "", null, false, "", outfit, [pic("x1"), pic("x2")]);
  check("single-picture model sends only the main heart", sent.refs.length === 1 && !sent.prompt.includes("Image 2"));
  let refused = "";
  try { await R("Alex and Sam", pic("a"), "4:3", undefined, "single", "", { first: "Alex", second: "Sam", blob: pic("b"), traits: "" }); } catch (err) { refused = err.message; }
  check("two people refused on a single-picture model", /only one reference picture/.test(refused), refused);

  // Two people on a 3-picture model: both hearts, one outfit picture.
  await R("Alex and Sam at the gala", pic("a"), "4:3", undefined, "three", "", { first: "Alex", second: "Sam", blob: pic("b"), traits: "", outfits: [{ blob: pic("o1"), title: "Gown" }, { blob: pic("o2"), title: "Tux" }] });
  check("pair on 3-picture model", JSON.stringify(await Promise.all(sent.refs.map(tag))) === JSON.stringify(["a", "b", "o1"]));

  // Over the prompt limit: learned likeness details and outfit notes survive, the scene is shortened.
  const traits = "Long base appearance notes about her face and body. ".repeat(10) + "Match these details of the reference especially closely: hair: ash-brown wolf cut; eyes: brown";
  const longScene = "Alex in a floor-length red silk gown with a deep V neckline, thigh-high slit, open back, gold heels, ".repeat(14);
  await R(longScene, pic("main"), "3:4", undefined, "seedream", traits, null, false, "", outfit, [pic("x1")]);
  check("shortening keeps what matters", sent.prompt.length <= 1500 && ["Match these details", "ash-brown wolf cut", "shows the outfit", "slit on the left leg", "same person"].every((k) => sent.prompt.includes(k)), "length " + sent.prompt.length);

  // Outfit reference choice.
  globalThis.writeCloset = async () => {}; globalThis.cardReference = async () => null;
  const likes = { "/p/a": { direction: "down" }, "/p/b": { direction: "up" } };
  check("outfit reference avoids likeness 👎, prefers 👍", (await O("ch1", { key: "k", picture: "/p/a", pictures: ["/p/c", "/p/b", "/p/a"] }, likes)) === "/p/b");
  check("outfit reference skips outfit 👎", (await O("ch1", { key: "k", picture: "/p/c", pictures: ["/p/c", "/p/d"], votes: { "/p/c": "down" } }, {})) === "/p/d");
  check("outfit reference chosen with ♡ stays", (await O("ch1", { key: "k", picture: "/p/a", pictureChosen: true, pictures: ["/p/a", "/p/b"] }, likes)) === "/p/a");
  console.log(fails ? fails + " FAILED" : "ALL PASSED");
  process.exit(fails ? 1 : 0);
})().catch((err) => { console.log("ERR", err); process.exit(1); });
