import { chromium } from "../../web/node_modules/playwright-core/index.mjs";
const b = await chromium.launch({ executablePath: "/usr/bin/google-chrome" });
const p = await b.newPage({ viewport: { width: 1200, height: 630 } });
await p.goto("file://" + process.cwd() + "/og.html"); await p.waitForTimeout(600);
await p.screenshot({ path: "../../web/public/og.png" });
for (const [size, out] of [[180, "apple-touch-icon.png"], [512, "logo-512.png"], [32, "favicon-32.png"]]) {
  await p.setViewportSize({ width: size, height: size });
  await p.goto("about:blank"); await p.setContent(`<html><body style="margin:0;background:transparent">${(await (await import("fs")).promises.readFile("favicon.svg","utf8")).replace("<svg ", `<svg width="${size}" height="${size}" `)}</body></html>`);
  await p.screenshot({ path: "../../web/public/" + out, omitBackground: true });
}
await b.close();
