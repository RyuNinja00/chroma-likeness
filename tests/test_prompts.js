// Prompt rules without a browser: hair accessories, shortening order, two-person outfit pictures, outfit reference choice.
// Run: node tests/test_prompts.js "extension/Chroma Likeness/extension.js"
const fs=require("fs"); const s=fs.readFileSync(process.argv[2],"utf8");
const grab=(n)=>{const i=s.indexOf(n);const j=s.indexOf("\n}\n",i);return s.slice(i,j+3)};
const line=(n)=>{const i=s.indexOf(n);return s.slice(i,s.indexOf("\n",i)+1)};
let sent=null, meta={edit:true,maxInputs:10,maxPrompt:1500};
const env = `
const adultAnchor="All people shown are adults.";
function modelMeta(){return meta} function savedModel(){return "seedream"} function imageKey(){return "k"} function wantsTags(){return false}
function withoutSelfieNote(x){return x}
async function spicyImage(prompt,model,ratio,w,h,refs){sent={prompt,refs};return {blob:new Blob([new Uint8Array([137,80,78,71,0,0,0,0,0,0,0,0])],{type:"image/png"}),cost:0}}
`;
eval(env + line("const hairWear") + line("const identityWords") + grab("function referenceEditPrompt") + grab("async function render(") + grab("async function outfitReference") + ";globalThis.R=render;globalThis.E=referenceEditPrompt;globalThis.O=outfitReference;");
(async()=>{
  // 1. hair accessories
  const e=E("She wears a red silk gown, a gold clip in her blonde hair, a wolf cut, green eyes, a ribbon in her hair","");
  console.log("1 HAIR:", e.slice(e.indexOf("Scene changes")));
  // 3. shortening order: long outfit scene, learned likeness focus must survive
  const traits="Long base appearance notes about her face and body. ".repeat(10)+"Match these details of the reference especially closely: hair: ash-brown wolf cut; eyes: brown";
  const longScene="Alex in a floor-length red silk gown with a deep V neckline, thigh-high slit, open back, gold heels, ".repeat(14);
  await R(longScene,new Blob(["a"]),"3:4",undefined,"seedream",traits,null,false,"",{blob:new Blob(["o"]),title:"Red silk gown",notes:["slit on the left leg"]});
  console.log("3 TRIM: length",sent.prompt.length,"<= 1500 |",["Match these details","ash-brown wolf cut","Image 2 shows the outfit","slit on the left leg"].map(k=>sent.prompt.includes(k)),"| refs",sent.refs.length);
  // 4. pair with two outfit pictures
  await R("Alex and Sam at the gala",new Blob(["a"]),"4:3",undefined,"seedream","",{first:"Alex",second:"Sam",blob:new Blob(["b"]),traits:"",outfits:[{blob:new Blob(["o1"]),title:"Red silk gown"},{blob:new Blob(["o2"]),title:"Black tux"}]});
  console.log("4 PAIR: refs",sent.refs.length,"|",sent.prompt.match(/Image \d shows the outfit for \w+/g));
  meta={edit:true,maxInputs:3};
  await R("Alex and Sam at the gala",new Blob(["a"]),"4:3",undefined,"seedream","",{first:"Alex",second:"Sam",blob:new Blob(["b"]),traits:"",outfits:[{blob:new Blob(["o1"]),title:"Red silk gown"},{blob:new Blob(["o2"]),title:"Black tux"}]});
  console.log("4 PAIR (3-image model): refs",sent.refs.length);
  // 2. outfit reference choice
  globalThis.writeCloset=async()=>{}; globalThis.cardReference=async()=>null;
  const likes={"/p/a":{direction:"down"},"/p/b":{direction:"up"}};
  console.log("2 PICK auto (ref has likeness 👎, b has 👍):", await O("ch1",{key:"k",picture:"/p/a",pictures:["/p/c","/p/b","/p/a"]},likes));
  console.log("2 PICK auto (no likeness votes, outfit 👎 on c):", await O("ch1",{key:"k",picture:"/p/c",pictures:["/p/c","/p/d"],votes:{"/p/c":"down"}},{}));
  console.log("2 PICK chosen with ♡ stays:", await O("ch1",{key:"k",picture:"/p/a",pictureChosen:true,pictures:["/p/a","/p/b"]},likes));
})().catch(e=>console.log("ERR",e));
