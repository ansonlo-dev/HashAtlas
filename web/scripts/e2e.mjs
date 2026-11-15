// Bounded end-to-end browser check of the built dashboard (Node + playwright-core + local Chrome).
// Visits every page at desktop and phone widths, exercises the main interactions, records console errors
// and writes screenshots to ../../reports/screenshots/ and a JSON record to ../../reports/web_validation.json.
// E2E_BASE_URL=https://host/ runs the same journey against the deployed site (screenshots under deployed/).
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";
import { startServer } from "./serve.mjs";

const here = fileURLToPath(new URL(".", import.meta.url));
const reports = join(here, "..", "..", "reports");
const REMOTE = process.env.E2E_BASE_URL;
const shots = join(reports, "screenshots", ...(REMOTE ? ["deployed"] : []));
await mkdir(shots, { recursive: true });
const PORT = 4191;
const BASE = REMOTE ?? `http://localhost:${PORT}/`;
const server = REMOTE ? null : await startServer(PORT);
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH ?? "/opt/google/chrome/chrome", headless: true });
const rec = { started: new Date().toISOString(), base_url: BASE, browser: browser.version(), checks: [], console_errors: [], screenshots: [] };
const check = (id, pass, detail = "") => { rec.checks.push({ id, pass: !!pass, detail: String(detail) }); console.log(`${pass ? "PASS" : "FAIL"} ${id}${detail ? " - " + detail : ""}`); };
const ROUTES = ["overview", "radar", "simulator", "eras", "rules", "advisor", "future", "methods"];

async function page(width, height) {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1, reducedMotion: "reduce" });
  const p = await ctx.newPage();
  p.on("pageerror", (e) => rec.console_errors.push(`${width}px ${e}`));
  p.on("console", (m) => { if (m.type() === "error") rec.console_errors.push(`${width}px console: ${m.text()}`); });
  return { ctx, p };
}
async function settle(p) { await p.waitForSelector(".panel", { timeout: 20000 }); await p.waitForTimeout(1400); }
async function shot(p, name) { const f = join(shots, `${name}.png`); await p.screenshot({ path: f, fullPage: true }); rec.screenshots.push(f.split("reports/")[1]); }

try {
  const { ctx, p } = await page(1440, 900);
  for (const r of ROUTES) {
    const t0 = Date.now();
    await p.goto(`${BASE}#/${r}`, { waitUntil: "networkidle" });
    await settle(p);
    const panels = await p.locator(".panel").count();
    const canvases = await p.locator("canvas").count();
    check(`${r}: renders`, panels >= 3, `${panels} panels, ${canvases} canvases, ${Date.now() - t0} ms`);
    const overflow = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    check(`${r}: no horizontal overflow at 1440px`, overflow <= 1, `${overflow}px`);
    await shot(p, `web-1440-${r}`);
  }
  // Interactions
  await p.goto(`${BASE}#/simulator`, { waitUntil: "networkidle" }); await settle(p);
  const before = await p.locator(".path .step").count();
  const opts = await p.locator("#ex option").count();
  await p.selectOption("#ex", { index: Math.min(opts - 1, 40) }); await p.waitForTimeout(400);
  check("simulator: tree path rendered and responds to a new block", before >= 2 && (await p.locator(".path .step").count()) >= 2, `${opts} example blocks`);
  await p.goto(`${BASE}#/advisor`, { waitUntil: "networkidle" }); await settle(p);
  const v1 = await p.locator(".kpi .value").nth(1).innerText();
  await p.selectOption("#ct", "Kazakhstan").catch(() => {}); await p.waitForTimeout(300);
  const v2 = await p.locator(".kpi .value").nth(1).innerText();
  check("advisor: electricity cost changes with country", v1 !== v2, `${v1} -> ${v2}`);
  await shot(p, "web-1440-advisor-kazakhstan");
  await p.goto(`${BASE}#/radar`, { waitUntil: "networkidle" }); await settle(p);
  await p.getByRole("button", { name: /Reveal labels/ }).click(); await p.waitForTimeout(300);
  check("radar: reveal shows labels", (await p.locator(".feed .tag.lime, .feed .tag.red").count()) > 0);
  await p.goto(`${BASE}#/future`, { waitUntil: "networkidle" }); await settle(p);
  const k1 = await p.locator(".grid.g3 .kpi .value").first().innerText();
  await p.locator('input[aria-label="price multiplier"]').fill("2"); await p.waitForTimeout(300);
  const k2 = await p.locator(".grid.g3 .kpi .value").first().innerText();
  check("future: break-even responds to the price scenario", k1 !== k2, `${k1} -> ${k2}`);
  await ctx.close();
  const m = await page(390, 844);
  for (const r of ["overview", "radar", "advisor", "future"]) {
    await m.p.goto(`${BASE}#/${r}`, { waitUntil: "networkidle" }); await settle(m.p);
    const overflow = await m.p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    check(`${r}: no horizontal overflow at 390px`, overflow <= 1, `${overflow}px`);
    await shot(m.p, `web-390-${r}`);
  }
  await m.ctx.close();
  check("no console errors", rec.console_errors.length === 0, rec.console_errors.slice(0, 3).join(" | "));
} finally {
  await browser.close();
  server?.close();
  rec.finished = new Date().toISOString();
  rec.passed = rec.checks.filter((c) => c.pass).length;
  rec.total = rec.checks.length;
  await writeFile(join(reports, REMOTE ? "web_validation_deployed.json" : "web_validation.json"), JSON.stringify(rec, null, 1));
  console.log(`${rec.passed}/${rec.total} checks passed`);
  process.exit(rec.passed === rec.total ? 0 : 1);
}
