import { chromium } from "../../web/node_modules/playwright-core/index.mjs";
const b = await chromium.launch({ executablePath: "/usr/bin/google-chrome" });
const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
await p.goto("file://" + process.cwd() + "/slides_bg.html");
for (const id of ["title", "section", "content"]) await (await p.$("#" + id)).screenshot({ path: `../assets/bg_${id}.png` });
await b.close();
