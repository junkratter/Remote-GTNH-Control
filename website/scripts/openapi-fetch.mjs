#!/usr/bin/env node
// Download the live OpenAPI spec from a running backend and write it to
// `src/api/openapi.json`. Usage:
//   node scripts/openapi-fetch.mjs http://127.0.0.1:8856
// Default URL is taken from BACKEND_URL env var.

import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const root = resolve(__dirname, "..");

const baseUrl = process.argv[2] || process.env.BACKEND_URL || "http://127.0.0.1:8856";
const url = `${baseUrl.replace(/\/$/, "")}/openapi.json`;

const target = resolve(root, "src/api/openapi.json");
mkdirSync(dirname(target), { recursive: true });

console.log(`Fetching ${url} …`);
const resp = await fetch(url);
if (!resp.ok) {
    console.error(`HTTP ${resp.status}`);
    process.exit(1);
}
const spec = await resp.json();
writeFileSync(target, JSON.stringify(spec, null, 2));
console.log(`Wrote ${target} (${Object.keys(spec.paths || {}).length} paths)`);
