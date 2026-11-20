#!/usr/bin/env node
// Chroma Likeness · SpicyAPI relay (optional)
//
// Only needed if SpicyAPI or NanoGPT ever refuses requests made from web pages (CORS). This tiny relay runs next to
// Marinara and forwards the Likeness extension's SpicyAPI and NanoGPT requests from outside the browser.
//
//   node likeness-relay.mjs                 → listens on http://127.0.0.1:7861 (this computer only)
//   HOST=0.0.0.0 node likeness-relay.mjs    → also reachable from your phone or other devices on your network
//   PORT=7900 node likeness-relay.mjs       → different port
//
// Needs Node 18 or newer. No packages to install. It keeps nothing on disk and never stores your key:
// the extension sends the key with each request and the relay passes it straight to the provider.
// It only forwards to spicyapi.ai, nano-gpt.com and the upload and result addresses SpicyAPI hands back.

import http from "node:http";

const PORT = Number(process.env.PORT) || 7861;
const HOST = process.env.HOST || "127.0.0.1";
const MAX_BYTES = 40 * 1024 * 1024;
// For local testing only: send *.spicyapi.ai traffic to another origin.
const REWRITE = process.env.RELAY_TEST_REWRITE || "";

const allowedHosts = new Set(["api.spicyapi.ai", "api.nano-gpt.com", "api.runware.ai", "im.runware.ai"]);
const isSpicy = (host) => host === "spicyapi.ai" || host.endsWith(".spicyapi.ai");
const isNano = (host) => host === "nano-gpt.com" || host.endsWith(".nano-gpt.com");

// Remember upload and result addresses that SpicyAPI returns, so the relay can reach them next.
function learnHosts(text) {
  for (const match of text.matchAll(/https:\/\/[^\s"'\\<>]+/g)) {
    try { allowedHosts.add(new URL(match[0]).hostname); } catch {}
  }
}

function cors(req, res) {
  res.setHeader("Access-Control-Allow-Origin", req.headers.origin || "*");
  res.setHeader("Vary", "Origin");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", req.headers["access-control-request-headers"] || "authorization, content-type, idempotency-key");
  res.setHeader("Access-Control-Max-Age", "600");
  // Lets pages served from a public address reach a relay on a private one (Chrome's private network checks).
  if (req.headers["access-control-request-private-network"]) res.setHeader("Access-Control-Allow-Private-Network", "true");
}

function fail(res, status, message) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ error: { message } }));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", (c) => {
      size += c.length;
      if (size > MAX_BYTES) { reject(new Error("Request body too large")); req.destroy(); return; }
      chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

const server = http.createServer(async (req, res) => {
  cors(req, res);
  if (req.method === "OPTIONS") { res.writeHead(204); res.end(); return; }
  const here = new URL(req.url, "http://relay");
  if (here.pathname === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true, relay: "chroma-likeness", version: 2 }));
    return;
  }
  if (here.pathname !== "/fetch") return fail(res, 404, "Unknown relay path.");
  if (!["GET", "POST", "PUT"].includes(req.method)) return fail(res, 405, "Method not allowed.");

  let target;
  try { target = new URL(here.searchParams.get("url") || ""); } catch { return fail(res, 400, "Missing or invalid url."); }
  if (target.protocol !== "https:") return fail(res, 400, "Only https addresses are relayed.");
  if (!isSpicy(target.hostname) && !isNano(target.hostname) && !allowedHosts.has(target.hostname))
    return fail(res, 403, "The relay only forwards to SpicyAPI, NanoGPT and addresses SpicyAPI returned: " + target.hostname);

  // Pass the request's own headers (presigned uploads can require extra ones), minus hop-by-hop and browser ones.
  const drop = /^(host|connection|content-length|origin|referer|cookie|accept-encoding|transfer-encoding|keep-alive|sec-|access-control-)/i;
  const headers = {};
  for (const [name, value] of Object.entries(req.headers)) if (!drop.test(name)) headers[name] = value;
  let destination = target.href;
  if (REWRITE && isSpicy(target.hostname)) destination = REWRITE + target.pathname + target.search;

  try {
    const body = req.method === "GET" ? undefined : await readBody(req);
    const upstream = await fetch(destination, { method: req.method, headers, body, redirect: "follow" });
    const buffer = Buffer.from(await upstream.arrayBuffer());
    const type = upstream.headers.get("content-type") || "application/octet-stream";
    if (isSpicy(target.hostname) && /json|text/.test(type)) learnHosts(buffer.toString("utf8"));
    res.writeHead(upstream.status, { "Content-Type": type });
    res.end(buffer);
    console.log(new Date().toISOString(), req.method, target.hostname + target.pathname, "→", upstream.status);
  } catch (e) {
    console.error(new Date().toISOString(), req.method, target.hostname + target.pathname, "failed:", e.message);
    fail(res, 502, "Relay could not reach " + target.hostname + ": " + e.message);
  }
});

server.listen(PORT, HOST, () => {
  const shown = HOST === "0.0.0.0" ? "http://<this computer's IP>:" + PORT : "http://" + HOST + ":" + PORT;
  console.log("Chroma Likeness relay running at " + shown);
  console.log("In Likeness → Settings, set “Relay address” to that address. Press Ctrl+C to stop.");
});
