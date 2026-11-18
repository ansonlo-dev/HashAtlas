// Build the slides, speaker script and timing sheet from pipeline outputs.
// Run ./make.sh from this directory to apply the theme, validate and render the PDF.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.join(__dirname, "..", "..");
const J = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), "utf8"));
const meta = J("web/public/data/meta.json");
const models = J("web/public/data/models.json");
const cl = J("artifacts/clusters.json");
const ru = J("artifacts/rules.json");
const dec = J("artifacts/decisions.json");
const fu = J("artifacts/future.json");
const q = J("artifacts/quality_report.json");
const ver = J("artifacts/verification.json");
const fsel = J("artifacts/feature_selection.json");
const team = J("configs/team.json");
const FIG = (n) => path.join(ROOT, "reports", "figures", "dark", `${n}.png`); // paper-toned slide variants
const ASSET = (n) => path.join(__dirname, "..", "assets", n);
const VIDEO = path.join(__dirname, "..", "video", "hashatlas_intro.mp4");
const POSTER = path.join(__dirname, "..", "video", "poster.png");
const VIDEO_S = (() => { try { return J("presentation/video/build/timing.json").total_s; } catch { return 90; } })();

// formatting
const n0 = (x) => Math.round(x).toLocaleString("en-US");
const f = (x, d = 2) => (x == null ? "n/a" : Number(x).toFixed(d));
const pc = (x, d = 0) => (x == null ? "n/a" : `${(100 * x).toFixed(d)}%`);
const odds = (p) => (!p ? "n/a" : p >= 0.2 ? pc(p, 0) : `1 in ${n0(1 / p)}`);

// theme
const HEAD = "Ubuntu", BODY = "Calibri", MONO = "Consolas";
const THEME = {
  name: "HashAtlas Ledger", headFontFace: HEAD, bodyFontFace: BODY,
  colors: { dk1: "1B1916", lt1: "FFFFFF", dk2: "2F4858", lt2: "F6F2EA", accent1: "F7931A", accent2: "2F4858",
    accent3: "1F7A6D", accent4: "B4432F", accent5: "4C78A8", accent6: "C9A227", hlink: "A65400", folHlink: "7B4B94" },
};
// Keep the existing colour keys for slide call sites.
const HEX = { bg: "F6F2EA", ink: "1B1916", card: "FFFDF9", card2: "EFE9DE", line: "E2D9CB", text: "1B1916", text2: "4A453F", muted: "776F65",
  btc: "F7931A", btcDeep: "A65400", violet: "2F4858", cyan: "1F7A6D", magenta: "B4432F", lime: "2E7D4F", blue: "4C78A8", red: "B4432F",
  gold: "C9A227", paper: "F6F2EA" };
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "HashAtlas: Can a Small Bitcoin Miner Still Win?";
pres.author = `Team ${team.team_name}`;
pres.subject = "CDS3004 Data Mining group project presentation";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };

pres.defineSlideMaster({
  title: "TITLE", background: { path: ASSET("bg_title.png") },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.05, w: 8.6, h: 2.2, fontSize: 55, bold: true, italic: true, fontFace: HEAD, color: "F6F2EA", valign: "top", align: "left", margin: 0 }, text: "" } }],
});
pres.defineSlideMaster({
  title: "SECTION", background: { path: ASSET("bg_section.png") },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.6, w: 11.7, h: 1.4, fontSize: 44, bold: true, italic: true, fontFace: HEAD, color: "F6F2EA", valign: "top", align: "left", margin: 0 }, text: "" } }],
});
pres.defineSlideMaster({
  title: "VIDEO", background: { color: HEX.ink }, objects: [],
});
const contentObjects = (footer) => [
  { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.36, w: 11.5, h: 0.8, fontSize: 36, bold: true, italic: true, fontFace: HEAD, color: HEX.ink, valign: "top", align: "left", margin: 0 }, text: "" } },
  { rect: { x: 0.6, y: 1.13, w: 0.75, h: 0.06, fill: { color: HEX.btc } } },
  { line: { x: 0.6, y: 6.98, w: 12.13, h: 0, line: { color: HEX.line, width: 0.75 } } },
  { text: { text: footer, options: { x: 0.6, y: 7.05, w: 7, h: 0.3, fontSize: 10, color: HEX.muted, charSpacing: 1.5, margin: 0, fontFace: BODY } } },
];
pres.defineSlideMaster({
  title: "CONTENT", background: { path: ASSET("bg_content.png") }, objects: contentObjects("HASHATLAS  ·  CDS3004 DATA MINING"),
  slideNumber: { x: 12.23, y: 7.04, w: 0.5, h: 0.3, fontSize: 10, color: HEX.muted, align: "right" },
});
pres.defineSlideMaster({
  title: "APPENDIX", background: { path: ASSET("bg_content.png") }, objects: contentObjects("APPENDIX  ·  backup for questions"),
  slideNumber: { x: 12.23, y: 7.04, w: 0.5, h: 0.3, fontSize: 10, color: HEX.muted, align: "right" },
});

// helpers
const T = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, color: HEX.text, valign: "top", align: "left", fontSize: 16, fontFace: BODY, ...o });
function card(s, x, y, w, h, o = {}) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: o.fill ?? HEX.card }, line: { color: o.line ?? HEX.line, width: o.lw ?? 0.75 }, objectName: o.name ?? "card",
    shadow: { type: "outer", color: "1B1916", opacity: 0.08, blur: 6, offset: 1.5, angle: 90 } });
  if (o.top) s.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.055, fill: { color: o.top }, line: { color: o.top, width: 0 }, objectName: "card accent" });
}
// Draw a square badge; keep hexBadge as the name used by slide call sites.
function hexBadge(s, x, y, label, color = HEX.btc, d = 0.62) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: d, h: d, fill: { color }, line: { color, width: 0 }, objectName: `badge ${label}` });
  T(s, label, { x, y, w: d, h: d, fontSize: d > 0.6 ? 15 : 13, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: MONO });
}
function stat(s, x, y, w, value, label, color = HEX.btcDeep, size = 40) {
  card(s, x, y, w, 1.6, { top: color === HEX.btcDeep ? HEX.btc : color });
  T(s, value, { x: x + 0.25, y: y + 0.22, w: w - 0.5, h: 0.8, fontSize: size + 3, italic: true, bold: true, color, fontFace: HEAD });
  T(s, label, { x: x + 0.25, y: y + 0.88, w: w - 0.42, h: 0.68, fontSize: 17, color: HEX.text2 });
}
const kicker = (s, text, x, y, w, color = HEX.btcDeep) => T(s, text, { x, y, w, h: 0.4, fontSize: 16, bold: true, color, charSpacing: 1 });
function img(s, file, x, y, w, h) {
  if (!fs.existsSync(file)) { T(s, `[missing ${path.basename(file)}]`, { x, y, w, h, color: HEX.red }); return; }
  const { w: pw, h: ph } = pngSize(file);
  const r = Math.min(w / pw, h / ph);
  const W = pw * r, H = ph * r;
  s.addImage({ path: file, x: x + (w - W) / 2, y: y + (h - H) / 2, w: W, h: H, altText: path.basename(file) });
}
function bitcoin(s, x, y, size) {
  T(s, "₿", { x, y, w: size, h: size, fontSize: size * 48, fontFace: "Noto Sans Display",
    color: HEX.btc, align: "center", valign: "middle" });
}
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
function bullets(s, items, x, y, w, h, o = {}) {
  s.addText(items.map((t, i) => {
    const parts = Array.isArray(t) ? t : [t];
    return parts.map((p, j) => ({ text: typeof p === "string" ? p : p.text,
      options: { bold: typeof p !== "string" && p.bold, color: typeof p !== "string" && p.color ? p.color : (o.color ?? HEX.text),
        bullet: j === 0 ? { code: "25AA", indent: 16 } : undefined, breakLine: j === parts.length - 1 && i < items.length - 1, paraSpaceAfter: 6 } }));
  }).flat(), { isTextBox: true, x, y, w, h, fontSize: o.size ?? 20, valign: "top", margin: 0, color: HEX.text, fontFace: BODY });
}
const chartBase = (title) => ({
  showTitle: !!title, title, titleColor: HEX.text, titleFontSize: 17, titleFontFace: BODY,
  catAxisLabelColor: HEX.text2, valAxisLabelColor: HEX.muted, catAxisLabelFontSize: 14, valAxisLabelFontSize: 13,
  catAxisLabelFontFace: BODY, valAxisLabelFontFace: BODY, valGridLine: { color: "E9E2D6", size: 0.75 }, catGridLine: { style: "none" },
  catAxisLineShow: false, valAxisLineShow: false, legendColor: HEX.text2, legendFontSize: 11, legendFontFace: BODY,
  dataLabelColor: HEX.text, dataLabelFontSize: 15, dataLabelFontFace: BODY,
});
// Put the presenter's name in the content-slide footer.
const tagPresenter = (s, name) => T(s, name, { x: 9.2, y: 7.05, w: 3.0, h: 0.3, fontSize: 10, color: HEX.btcDeep, align: "right", bold: true });

const SCRIPT = [];
const WPM = 130;
const words = (t) => (t || "").replace(/\[[^\]]*\]/g, "").split(/\s+/).filter(Boolean).length;
// Speaking time = words at 130 wpm + 8 s per slide for pointing and hand-overs. `fixed` keeps a set slot (demo).
// `video` is playback time on the slide (not spoken); it is shown separately in the timing sheet.
function slide(master, section, presenter, title, notes, o = {}) {
  const speech = o.fixed ?? (notes ? Math.round(words(notes) / WPM * 60 + 8) : 0);
  const video = o.video ?? 0;
  const s = pres.addSlide({ masterName: master, sectionTitle: section });
  if (title) s.addText(title, { placeholder: "title", fontFace: HEAD, bold: true, italic: true });
  if (notes) s.addNotes(`${presenter ? presenter + " · " : ""}~${speech}s speaking${video ? ` + ${video}s video` : ""} · ${notes}`);
  if (presenter && (master === "CONTENT")) tagPresenter(s, presenter);
  SCRIPT.push({ n: SCRIPT.length + 1, section, presenter, title: title || "(title)", seconds: speech, video, notes, timed: !o.untimed });
  return s;
}
const M = team.members.map((m) => m.name);
const op = models.test.operational_family;
const TF = models.test.families;
const FAM = { tree: "Decision tree", knn: "KNN", svm_linear: "Linear SVM", svm_rbf: "RBF SVM", decision_stump: "Stump", stratified_random: "Random", majority: "Majority" };
const st = dec.network_state;
const adv = dec.advisor;
const s21 = adv.filter((a) => a.device === "Antminer S21" && a.tariff === "business").sort((a, b) => a.price_usd_kwh - b.price_usd_kwh);
const s21be = s21[0].breakeven_usd_kwh;
const hkS21 = adv.find((a) => a.device === "Antminer S21" && a.country === "Hong Kong" && a.tariff === "business");
const bitaxe = adv.find((a) => a.device.startsWith("Bitaxe") && a.country === "Hong Kong" && a.tariff === "business");
const soloYears = q.labels.solo_blocks;
const ward = cl.hierarchical.ward;
const multiFam = cl.pool_families.families.filter((g) => g.length > 1);
const sigs = ru.pool_signatures.filter((s) => s.top.length);
const recentSolo = J("web/public/data/whomines.json").solo_by_year;
const ua = dec.unknown_attribution;
const nb = dec.new_blocks;
const topRule = ru.rules.length ? ru.rules.slice().sort((a, b) => b.lift - a.lift)[0] : null;

// M1 · 1. Title
pres.addSection({ title: "Opening" });
{
  const s = slide("TITLE", "Opening", M[0], "Can a small Bitcoin miner still win?",
    "Imagine plugging a Bitcoin miner into a Hong Kong wall socket. Would you join a pool, try solo, or switch it off? Keep your choice in mind.");
  bitcoin(s, 10.75, 3.65, 1.45);
  T(s, "HASHATLAS", { x: 0.8, y: 1.3, w: 8, h: 0.5, fontSize: 18, bold: true, color: HEX.btc, charSpacing: 8 });
  T(s, `What ${n0(q.rows_loaded)} blocks tell us about mining pools and the cost of mining in Hong Kong`, { x: 0.8, y: 4.3, w: 8.4, h: 0.9, fontSize: 24, color: "E2DACF" });
  team.members.forEach((member, i) => {
    const x = 0.8 + i * 2.42;
    T(s, member.name, { x, y: 5.55, w: 2.35, h: 0.35, fontSize: 18, bold: true, color: HEX.paper });
    T(s, member.student_id + (member.captain ? " · Captain" : ""), { x, y: 5.97, w: 2.35, h: 0.35, fontSize: 15, color: "D6CBB9" });
  });
  T(s, `CDS3004 Data Mining  ·  Lingnan University  ·  CRN ${team.crn}  ·  ${team.live_site.replace("https://", "").replace(/\/$/, "")}`, { x: 0.8, y: 6.65, w: 11.8, h: 0.4, fontSize: 13, color: "A39A8D" });
}

// M1 · 2. Video
{
  const s = slide("VIDEO", "Opening", M[0], "",
    `[Click to play the ${VIDEO_S}-second introduction video; do not talk over it. When it ends:] Let’s look at the evidence.`, { video: VIDEO_S });
  T(s, "INTRODUCTION  ·  " + `${Math.floor(VIDEO_S / 60)}:${String(VIDEO_S % 60).padStart(2, "0")}`, { x: 1.47, y: 0.42, w: 6, h: 0.35, fontSize: 12, bold: true, color: HEX.btc, charSpacing: 4 });
  if (fs.existsSync(VIDEO)) {
    const cover = fs.existsSync(POSTER) ? "data:image/png;base64," + fs.readFileSync(POSTER).toString("base64") : undefined;
    img(s, POSTER, 1.47, 0.9, 10.4, 5.85);
    s.addMedia({ type: "video", path: VIDEO, x: 1.47, y: 0.9, w: 10.4, h: 5.85, ...(cover ? { cover } : {}) });
  } else {
    card(s, 1.47, 0.9, 10.4, 5.85, { fill: "24211D", line: "3A352F" });
    T(s, "[video: presentation/video/hashatlas_intro.mp4]", { x: 1.47, y: 3.6, w: 10.4, h: 0.5, fontSize: 16, color: "A39A8D", align: "center" });
  }
  T(s, "Also on the dashboard · " + team.live_site.replace("https://", "").replace(/\/$/, ""), { x: 1.47, y: 6.9, w: 10.4, h: 0.3, fontSize: 11, color: "8C8478", align: "right" });
}

// M1 · 3. Questions
{
  const s = slide("CONTENT", "Opening", M[0], "What can a block reveal about its miner?",
    `We asked three questions. First, from a block's behaviour alone, never its name, can we tell who mined it? Second, clustering and association rules: do the data rediscover the CPU, GPU and ASIC eras on their own, and which pools build blocks alike? Third, decision making: should a miner in Hong Kong join a pool, mine solo as a lottery, or switch off, today and after the 2028 halving?`);
  stat(s, 0.6, 1.5, 3.9, odds(bitaxe.solo_p_block_per_year), "annual chance of a solo win at 1.2 TH/s", HEX.magenta, 38);
  stat(s, 4.7, 1.5, 3.9, `${recentSolo["2025"] ?? 0} + ${recentSolo["2026"] ?? 0}`, "solo wins in 2025 and 2026 to the freeze", HEX.btcDeep, 38);
  stat(s, 8.8, 1.5, 3.9, `${f(st.hashrate_ths_30d / 1e6, 0)} EH/s`, "network hash rate, 31 Oct 2026", HEX.violet, 38);
  const qs = [["Q1", "CLASSIFY", "Can block behaviour identify the miner?", HEX.violet],
    ["Q2", "CLUSTER + RULES", "Which mining eras and pool families emerge?", HEX.cyan],
    ["Q3", "DECIDE", "When does mining cover the power bill?", HEX.btcDeep]];
  qs.forEach(([k, t, d, c], i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 3.45, 3.9, 3.0);
    hexBadge(s, x + 0.3, 3.75, k, c === HEX.btcDeep ? HEX.btc : c);
    T(s, t, { x: x + 1.1, y: 3.88, w: 2.6, h: 0.45, fontSize: 16, bold: true, color: c, charSpacing: 1 });
    T(s, d, { x: x + 0.3, y: 4.65, w: 3.3, h: 1.6, fontSize: 23, color: HEX.text });
  });
}

// M1 · 4. Problem
{
  const s = slide("CONTENT", "Opening", M[0], "What makes miner identification difficult?",
    "Five constraints shaped our design. API rate limits meant our downloads had to resume after an interruption. Labels are self-declared: a pool's name is text written into the block, so it is the label and never an input. No look-ahead: we train on the past and test on the most recent period. Solo blocks are extremely rare. And we report costs and uncertainty. We rejected four alternatives: predicting the price, simply reading the tag, tracing transactions, and black-box deep learning.");
  card(s, 0.6, 1.5, 5.9, 4.95, { top: HEX.btc });
  kicker(s, "CONSTRAINTS", 0.9, 1.75, 5);
  bullets(s, [[{ text: "Self-declared labels", bold: true }, ": the coinbase tag is the label, never a feature"],
    [{ text: "No look-ahead", bold: true }, ": train 2019-23, validate 2024-25Q1, sealed test 2025Q2-26"],
    [{ text: "Extreme imbalance", bold: true }, `: only ${soloYears} solo blocks in 17 years`],
    [{ text: "Rate-limited sources", bold: true }, ": resumable, hashed, audited acquisition"],
    [{ text: "Ethics", bold: true }, ": pseudonymous data; odds, not financial advice"]], 0.9, 2.25, 5.4, 4, { size: 20 });
  card(s, 6.8, 1.5, 5.9, 4.95, { top: HEX.violet });
  kicker(s, "ALTERNATIVES CONSIDERED", 7.1, 1.75, 5.3, HEX.violet);
  const alts = [["Predict the BTC price", "not about mining; driven by outside events"], ["Look up the coinbase tag", "that is the label; fails when tags are missing"],
    ["Trace transactions", "billions of rows; re-identification risk"], ["Deep learning on raw bytes", "uninterpretable; outside course scope"]];
  alts.forEach(([a, b], i) => {
    T(s, "×", { x: 7.1, y: 2.33 + i * 0.95, w: 0.4, h: 0.4, fontSize: 18, bold: true, color: HEX.red });
    T(s, a, { x: 7.55, y: 2.3 + i * 0.95, w: 4.9, h: 0.4, fontSize: 20, bold: true, color: HEX.text });
    T(s, b, { x: 7.55, y: 2.68 + i * 0.95, w: 4.9, h: 0.5, fontSize: 17, color: HEX.text2 });
  });
}

// M1 · 5. Data
pres.addSection({ title: "Data" });
{
  const s = slide("CONTENT", "Data", M[0], `${n0(q.rows_loaded)} blocks, zero gaps, audited labels`,
    `Our table includes the November follow-up blocks, ${n0(q.rows_loaded)} of them. Blockchair's daily dumps cover 2009 to 2018; from 2019 we pulled blocks pool by pool from mempool.space, about ${n0(J("artifacts/source_manifest.json").mempool_blocks.calls)} API calls. The final table has zero missing and zero duplicate heights. To trust our labels, we compared our own tag-matching labeller with mempool.space on ${n0(q.label_audit.blocks_compared)} blocks: when it finds a tag, the two sources agree ${pc(q.label_audit.precision_when_tag_found, 2)} of the time. ${M[1]} will now explain our features.`);
  stat(s, 0.6, 1.45, 2.95, n0(q.rows_loaded), "blocks, heights 0 → " + n0(q.height_range[1]), HEX.btcDeep, 30);
  stat(s, 0.6, 3.2, 2.95, `${q.missing_heights} / ${q.duplicate_heights}`, "missing / duplicate heights", HEX.lime, 30);
  stat(s, 0.6, 4.95, 2.95, pc(q.label_audit.precision_when_tag_found, 2), `tag agreement when matched`, HEX.cyan, 30);
  card(s, 3.8, 1.45, 8.9, 5.1);
  img(s, FIG("f02_who_mines"), 3.95, 1.6, 8.6, 4.8);
}

// M2 · 6. Features
pres.addSection({ title: "Features & models" });
{
  const s = slide("CONTENT", "Features & models", M[1], "How we built a miner fingerprint",
    "Thank you. A block header contains a 32-bit version field and a 32-bit nonce. They are stored as integers, but they are really nominal bit fields, so we decomposed them into individual bits. This matters because the coinbase text can be missing or copied, so behaviour is the one signal a pool cannot simply rename. Modern ASIC miners roll the general-purpose version bits 13 to 28, and pools differ in how many bits they roll. From the block body we built ratios such as fullness and witness share. We also built day-relative features: each block's fee level or size minus that day's median, which removes market conditions and leaves only the miner's policy. We deliberately added the hour of day as a control feature that should be useless. And we excluded everything that leaks the label: coinbase text, payout address, height and calendar time.");
  const cols = [["HEADER", HEX.violet, ["version → 16 rolling bits, rolled-bit count, signal bits", "nonce → 32 binary bits", "timestamp → offset vs median-of-11, interval"]],
    ["BODY", HEX.cyan, ["fullness = weight / 4M", "witness share, inputs vs outputs", "fee rate, fee percentiles (log1p)"]],
    ["DAY-RELATIVE", HEX.btcDeep, ["fee rate − day median", "tx count − day median", "fullness − day median"]]];
  cols.forEach(([t, c, items], i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.5, 3.9, 3.2, { top: c === HEX.btcDeep ? HEX.btc : c });
    kicker(s, t, x + 0.3, 1.75, 3.3, c);
    bullets(s, items, x + 0.3, 2.3, 3.4, 2.3, { size: 19 });
  });
  card(s, 0.6, 4.95, 6.0, 1.6, { top: HEX.red });
  kicker(s, "EXCLUDED (LEAKAGE)", 0.9, 5.15, 5.4, HEX.red);
  T(s, "coinbase text · payout address · Blockchair miner guess · height · calendar time · difficulty", { x: 0.9, y: 5.6, w: 5.5, h: 0.9, fontSize: 19 });
  card(s, 6.8, 4.95, 5.9, 1.6, { top: HEX.lime });
  kicker(s, "CONTROL FEATURE", 7.1, 5.15, 5.4, HEX.lime);
  T(s, "Hour of day (sine and cosine) dropped out during selection.", { x: 7.1, y: 5.6, w: 5.4, h: 0.9, fontSize: 19 });
}

// M2 · 7. Selection
{
  const g = fsel.group_ablation.groups;
  const s = slide("CONTENT", "Features & models", M[1], `Feature selection: ${fsel.candidates} → ${fsel.n_selected}`,
    `Selection used the training data only, and moved from filters to a wrapper. First a variance filter removed near-constant features. Then mutual information was compared with ten random noise probes: anything no better than noise was dropped, ${fsel.removed_mi_below_noise.length} features in total, including both timestamp features. That is a finding in itself: block discovery is a random process for every miner, so timing carries no fingerprint. Next we removed redundant pairs with Spearman correlation above 0.9. Finally, a group ablation on the right: removing the version bits or the body-composition group clearly hurts the cross-validated score, while the hour-of-day control does nothing and was removed. That left us with ${fsel.n_selected} features.`);
  const steps = [[fsel.candidates, "candidates"], [fsel.candidates - fsel.removed_low_variance.length, "after variance filter"],
    [fsel.candidates - fsel.removed_low_variance.length - fsel.removed_mi_below_noise.length, "MI above noise probes"],
    [fsel.candidates - fsel.removed_low_variance.length - fsel.removed_mi_below_noise.length - fsel.removed_redundant.length, "non-redundant (|ρ| ≤ 0.9)"],
    [fsel.n_selected, "after group ablation"]];
  const fc = [HEX.violet, HEX.blue, HEX.cyan, HEX.gold, HEX.btc];
  steps.forEach(([v, l], i) => {
    const w = 5.5 - i * 0.32;
    const x = 0.6 + (5.2 - w) / 2;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.55 + i * 1.0, w, h: 0.82, fill: { color: fc[i], transparency: 82 }, line: { color: fc[i], width: 1.25 }, objectName: `funnel ${i}` });
    T(s, `${v}`, { x: x + 0.2, y: 1.62 + i * 1.0, w: 1.2, h: 0.7, fontSize: 26, bold: true, valign: "middle", fontFace: HEAD });
    T(s, l, { x: x + 1.35, y: 1.62 + i * 1.0, w: w - 1.5, h: 0.7, fontSize: 18, valign: "middle" });
  });
  const names = Object.keys(g);
  s.addChart(pres.charts.BAR, [{ name: "Δ CV macro-F1 when removed", labels: names, values: names.map((k) => g[k].change) }], {
    x: 6.4, y: 1.45, w: 6.3, h: 5.1, barDir: "bar", ...chartBase("Change in macro-F1 after removing each group"), showLegend: false, catAxisLabelPos: "low",
    chartColors: [HEX.btc], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "+0.000;-0.000", valAxisLabelFormatCode: "0.00" });
}

// M2 · 8. Validation design
{
  const S = models.search;
  const sp = models.split;
  const s = slide("CONTENT", "Features & models", M[1], "How we tested on future blocks",
    `How we learned the models matters as much as which models we used. Shuffled cross-validation would put blocks from the same day on both sides of a split and overstate accuracy, so our folds are grouped by calendar month. We tuned a decision tree, KNN, and both linear and RBF support vector machines on the 2019-to-2023 training period; the table shows the selected settings and how each model scored. Nested cross-validation estimates the whole tuning procedure for the tree at ${f(models.nested_cv.mean, 3)} macro-F1, which gives us a check on selection bias. Finally, the model choice and the solo threshold were frozen on the out-of-time validation period, before the sealed test was ever opened. ${M[2]} will now show what happened on that test.`);
  const segs = [["TRAIN", `${sp.train.first.slice(0, 4)}–${sp.train.last.slice(0, 4)}`, `${n0(sp.train.labelled)} blocks`, HEX.violet, 5.0],
    ["VALIDATION", "2024 – 2025Q1", `${n0(sp.validation.labelled)} blocks`, HEX.cyan, 2.6], ["SEALED TEST", "2025Q2 – 2026-10", `${n0(sp.test.labelled)} blocks`, HEX.btc, 3.1],
    ["NEW", "Nov 2026", `${n0(sp.new.labelled)} blocks`, HEX.magenta, 1.4]];
  let x = 0.6;
  segs.forEach(([t, d, nbk, c, w]) => {
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.5, w: w - 0.08, h: 1.3, fill: { color: c, transparency: 84 }, line: { color: c, width: 1.25 }, objectName: `split ${t}` });
    T(s, t, { x: x + 0.15, y: 1.6, w: w - 0.3, h: 0.35, fontSize: 13, bold: true, color: c === HEX.btc ? HEX.btcDeep : c, charSpacing: 2 });
    T(s, d, { x: x + 0.15, y: 1.95, w: w - 0.3, h: 0.35, fontSize: 15, bold: true });
    T(s, nbk, { x: x + 0.15, y: 2.32, w: w - 0.3, h: 0.35, fontSize: 13, color: HEX.text2 });
    x += w;
  });
  const rows = [["Model", "Chosen settings", "CV macro-F1"]].concat(["tree", "knn", "svm_linear", "svm_rbf"].map(k => {
    const p = S[k].best_params;
    const setting = {tree: `${p.criterion}, depth ${p.max_depth}, minimum leaf ${p.min_samples_leaf}`,
      knn: `${p.model__n_neighbors} neighbours, ${p.model__metric}, distance weights`,
      svm_linear: `C = ${p.model__C}`, svm_rbf: `C = ${p.model__C}, γ = ${p.model__gamma}`}[k];
    return [FAM[k], setting, `${f(S[k].cv_macro_f1_mean, 3)} ± ${f(S[k].cv_macro_f1_se, 3)}`];
  }));
  s.addTable(rows, { x: 0.6, y: 3.05, w: 12.1, colW: [2.65, 6.75, 2.7], fontSize: 19, fontFace: BODY,
    fill: { color: HEX.card }, color: HEX.ink, border: { type: "solid", color: HEX.line, pt: 0.8 }, margin: 0.09 });
  T(s, `Folds grouped by month · nested CV (5 × 3) for the tree: ${f(models.nested_cv.mean, 3)} ± ${f(models.nested_cv.sd, 3)} · choice frozen ${models.selection.frozen_at.slice(0, 10)} before the test was opened`, { x: 0.6, y: 6.25, w: 12.1, h: 0.5, fontSize: 14, color: HEX.text2 });
}

// M3 · 9. Results
pres.addSection({ title: "Results" });
{
  const names = ["tree", "knn", "svm_linear", "svm_rbf", "decision_stump", "stratified_random", "majority"];
  const s = slide("CONTENT", "Results", M[2], "How well does the tree identify a pool?",
    `Thank you. On the sealed test period the decision tree is clearly best: macro-F1 ${f(TF[op].macro_f1, 3)}, with a bootstrap interval of ${f(models.test.bootstrap.macro_f1_95ci[0], 2)} to ${f(models.test.bootstrap.macro_f1_95ci[1], 2)}, about ${f(TF[op].macro_f1 / TF.stratified_random.macro_f1, 1)} times the random baseline. Macro-F1 is our main metric because it weighs every pool equally, so a model cannot score well by predicting only the largest pools. KNN and the SVMs struggle, because the signal sits in a few discrete bit patterns that tree splits isolate, while distances and kernels dilute them across fifty features. On the right are three accuracies: the exact pool is right ${pc(TF[op].accuracy)} of the time, against ${pc(TF.majority.accuracy)} for always guessing the largest pool, and the true pool is among the tree's top three ${pc(TF[op].top3_accuracy)} of the time. So behaviour narrows a block down to a few look-alike pools.`);
  s.addChart(pres.charts.BAR, [
    { name: "Sealed test macro-F1", labels: names.map((k) => FAM[k]), values: names.map((k) => TF[k].macro_f1) },
  ], { x: 0.6, y: 1.45, w: 7.2, h: 5.1, barDir: "col", ...chartBase("Macro-F1 on the sealed test"), showLegend: false,
    chartColors: names.map((k) => (k === op ? HEX.btc : ["tree", "knn", "svm_linear", "svm_rbf"].includes(k) ? HEX.violet : "CFC2AE")),
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", valAxisLabelFormatCode: "0.0", valAxisMinVal: 0 });
  stat(s, 8.1, 1.45, 4.6, pc(TF[op].accuracy), `exact pool (${models.selection.classes.length} classes)`, HEX.violet, 34);
  stat(s, 8.1, 3.2, 4.6, pc(TF[op].top3_accuracy), "true pool among the top 3 candidates", HEX.btcDeep, 34);
  stat(s, 8.1, 4.95, 4.6, pc(TF.majority.accuracy), "always guessing the largest pool (baseline)", HEX.muted, 34);
}

// M3 · 10. Confusion
{
  const top = models.test.newcomer_pools.slice(0, 2);
  const s = slide("CONTENT", "Results", M[2], "Who looks like whom?",
    `The confusion matrix shows where the errors go. Pools with a distinctive habit, such as signalling bits or an unusual number of rolled version bits, sit on the diagonal. The largest pools blur into each other, because since 2023 almost everyone fills blocks with the same fee-maximising template. A strong test of this idea is pools that did not exist in training: ${top.map((r) => `${r.miner} is predicted as ${r.top_prediction} ${pc(r.top_share)} of the time`).join(", and ")}. So the model is recognising a block template, not a brand name, which is why top-three accuracy matters. Modern solo blocks look like pool blocks too: the solo class reaches an average precision of ${f(TF[op].solo_average_precision ?? TF.tree.solo_average_precision, 2)}, against a base rate of ${pc(TF.tree.solo_base_rate, 2)}.`);
  card(s, 0.6, 1.45, 6.6, 5.1);
  img(s, FIG("f08_confusion"), 0.75, 1.55, 6.3, 4.9);
  card(s, 7.45, 1.45, 5.25, 5.1, { top: HEX.btc });
  kicker(s, "NEWCOMERS: WHOSE TEMPLATE?", 7.75, 1.7, 4.8);
  models.test.newcomer_pools.slice(0, 6).forEach((r, i) => {
    T(s, r.miner, { x: 7.75, y: 2.25 + i * 0.62, w: 2.2, h: 0.4, fontSize: 19, bold: true });
    T(s, `→ ${r.top_prediction}`, { x: 9.9, y: 2.25 + i * 0.62, w: 1.9, h: 0.4, fontSize: 19, color: HEX.cyan });
    T(s, pc(r.top_share), { x: 11.75, y: 2.25 + i * 0.62, w: 0.8, h: 0.4, fontSize: 19, bold: true, color: HEX.btcDeep, align: "right" });
  });
  T(s, "Pools absent from training, mapped by the frozen model (validation + test blocks)", { x: 7.75, y: 6.0, w: 4.8, h: 0.45, fontSize: 12, color: HEX.muted });
}

// M3 · 11. New examples
{
  const s = slide("CONTENT", "Results", M[2], "What happened after we froze the model?",
    `Finally, we applied the frozen model to new examples, in two ways. First, ${n0(ua.unknown_blocks)} blocks from the last year carry no pool tag at all; the model assigns each one, ${pc(ua.high_confidence_share)} of them with high confidence. Second, a true out-of-time check: ${n0(nb.labelled)} blocks mined after our data freeze, from the first to the twelfth of November. We predicted first and revealed the labels afterwards: ${pc(nb.accuracy)} were exactly right, a little below the sealed test, which reminds us that fingerprints drift and the model must be retrained. The same fingerprints also measure concentration: by pool name, ${ua.nakamoto_by_pool_name} pools mine half of all blocks; if look-alike families were one builder, it would be ${ua.nakamoto_after_family_merge}. That is an upper bound, not proof. ${M[3]} continues with clustering.`);
  stat(s, 0.6, 1.45, 3.9, n0(ua.unknown_blocks), `untagged blocks; ${pc(ua.high_confidence_share)} at high confidence`, HEX.violet, 34);
  stat(s, 4.7, 1.45, 3.9, pc(nb.accuracy), `exactly right on ${n0(nb.labelled)} blocks mined after the freeze`, HEX.btcDeep, 34);
  stat(s, 8.8, 1.45, 3.9, `${ua.nakamoto_by_pool_name} → ${ua.nakamoto_after_family_merge}`, "pools for 50% of blocks, before / after grouping", HEX.magenta, 34);
  card(s, 0.6, 3.3, 12.1, 3.25, { top: HEX.ink });
  kicker(s, `PREDICTIONS AND REVEALED LABELS · SAMPLE`, 0.9, 3.55, 11.5, HEX.ink);
  // evenly spaced over all revealed examples (not hand-picked), newest first
  const ex = Array.from({ length: 4 }, (_, i) => nb.examples[Math.round((i * (nb.examples.length - 1)) / 3)]).reverse();
  ex.forEach((e, i) => {
    const y = 4.14 + i * 0.55;
    T(s, `#${n0(e.height)}`, { x: 0.9, y, w: 1.6, h: 0.35, fontSize: 18, bold: true, color: HEX.btcDeep, fontFace: MONO });
    T(s, e.time.slice(5, 16).replace("T", " ") + " UTC", { x: 2.5, y, w: 2.6, h: 0.35, fontSize: 16, color: HEX.muted, fontFace: MONO });
    T(s, `predicted ${e.predicted}`, { x: 5.2, y, w: 3.4, h: 0.35, fontSize: 18 });
    T(s, `revealed ${e.revealed_label}`, { x: 8.6, y, w: 3.0, h: 0.35, fontSize: 18, color: HEX.text2 });
    T(s, e.correct ? "✓" : "✕", { x: 11.9, y, w: 0.5, h: 0.35, fontSize: 16, bold: true, color: e.correct ? HEX.lime : HEX.red, align: "right" });
  });
}

// M4 · 12. Eras
{
  const s = slide("CONTENT", "Results", M[3], "Weekly block patterns reveal three mining eras",
    `Thank you. Now, clustering. We built one row per week, with nine features describing how blocks were produced, and never the dates of the hardware eras. K-means, with K chosen by silhouette because the error curve keeps falling without a clear elbow, four hierarchical linkages and DBSCAN all ran on the same rows. Only afterwards did we compare the clusters with documented history: Ward linkage reaches an adjusted Rand index of ${f(ward.ari_vs_hardware_eras, 2)}, and K-means ${f(cl.ari_vs_hardware_eras.kmeans, 2)}. Three eras emerge: the hobbyist CPU and GPU years, the FPGA-to-early-ASIC transition, and the industrial era. Ward's second boundary falls two days after the 2016 halving. DBSCAN, on the other hand, marks the fast transition weeks as noise: density-based clustering cannot separate eras that blend into each other.`);
  card(s, 0.6, 1.45, 12.1, 3.2);
  img(s, FIG("f13_eras_timeline"), 0.75, 1.55, 11.8, 3.0);
  stat(s, 0.6, 4.95, 2.9, f(ward.ari_vs_hardware_eras, 2), "ARI, Ward vs documented eras", HEX.btcDeep, 34);
  stat(s, 3.65, 4.95, 2.9, f(cl.ari_vs_hardware_eras.kmeans, 2), `ARI, K-means (K = ${cl.k_selected})`, HEX.violet, 34);
  stat(s, 6.7, 4.95, 2.9, f(cl.seed_stability_ari_mean, 2), "K-means stability over seeds", HEX.cyan, 34);
  stat(s, 9.75, 4.95, 2.95, pc(cl.dbscan_selected.noise_share, 1), "weeks DBSCAN calls noise", HEX.magenta, 34);
}

// M4 · 13. Families + rules
{
  const s = slide("CONTENT", "Results", M[3], "Pool families and block signatures",
    `Clustering the pools themselves by their average fingerprint gives families: ${multiFam.slice(0, 2).map((g) => g.join(" plus ")).join("; and ")}. This agrees with the classifier, which read newcomers as the pool closest to them. Association rules tell the same story from another angle. Our from-scratch Apriori, checked against a brute-force count, found rules such as ${topRule ? topRule.antecedent.join(" and ") + " implies " + topRule.consequent.replace("miner=", "") + ", with a lift of " + f(topRule.lift, 0) : "few strong rules"}. Lift matters here: confidence alone would favour the largest pools, so we keep only rules whose lift is well above one. Contrast mining inside each pool gives the signatures on the right, while some large pools have no distinctive rule at our thresholds. Similar fingerprints suggest shared templates or software; they do not prove common ownership.`);
  card(s, 0.6, 1.45, 7.0, 5.1);
  img(s, FIG("f14_pool_dendrogram"), 0.75, 1.55, 6.7, 4.9);
  card(s, 7.85, 1.45, 4.85, 5.1, { top: HEX.btc });
  kicker(s, "Pattern frequency: inside vs outside", 8.1, 1.7, 4.5);
  sigs.slice(0, 3).forEach((sg, i) => {
    const t = sg.top[0];
    const y = 2.33 + i * 1.19;
    T(s, sg.pool, { x: 8.1, y, w: 2.6, h: 0.42, fontSize: 21, bold: true });
    T(s, `${f(t.ratio, 1)}×`, { x: 10.65, y, w: 1.8, h: 0.42, fontSize: 23, bold: true, color: HEX.cyan, align: "right" });
    const description = t.itemset.map(item => item.replace("fullness=full(>=98%)", "≥98% full").replace("version=", "")).join(" + ");
    T(s, description, { x: 8.1, y: y + 0.46, w: 4.25, h: 0.68, fontSize: 17, color: HEX.text2 });
  });
  T(s, `Apriori: ${n0(ru.transactions)} blocks · ${ru.frequent_itemsets} frequent itemsets · brute-force check ${ru.brute_force_check.passed ? "passed" : "FAILED"}`, { x: 8.1, y: 6.15, w: 4.5, h: 0.35, fontSize: 13, color: HEX.muted });
}

// M4 · 14. Limits + verification
{
  const webv = J("reports/web_validation.json");
  const s = slide("CONTENT", "Results", M[3], "What our checks caught",
    `Before the decisions, three honest limits. Labels are self-declared, fingerprints drift so the model is dated, and the solo class rests on only a few dozen test blocks. A single extra correct prediction can move recall for that class. We used AI coding agents throughout, but a person verified every stage, and some agent outputs were wrong. We caught a macro-F1 that counted pools which no longer exist, an association-rule run that returned zero rules because the threshold ignored base rates, and a forecasting method that overshot its own backtest. Our independent verification recomputes ${ver.total} key results through separate code paths, and all ${ver.passed} pass; the deck reads these checks from the pipeline outputs. ${M[4]} will now turn the results into decisions.`);
  const cols = [["LIMITS", HEX.red, ["Labels are self-declared; may be shared", "Fingerprints drift; retrain regularly", `Solo class: ${models.split.test.solo} test blocks`, "Retail tariffs; scenarios, not forecasts"]],
    ["AGENT ERRORS WE CAUGHT", HEX.violet, ["Macro-F1 over vanished pools: fixed", "Zero-rule Apriori run: thresholds fixed", "Backtest favoured no growth", "Team reviewed each fix"]],
    ["INDEPENDENT CHECKS", HEX.lime, [`${ver.passed}/${ver.total} recomputations pass`, "Apriori vs brute force: identical", "K-means step vs scikit-learn: identical", `${webv.passed}/${webv.total} browser checks`]]];
  cols.forEach(([t, c, items], i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.5, 3.9, 3.35, { top: c });
    kicker(s, t, x + 0.3, 1.75, 3.4, c);
    bullets(s, items, x + 0.3, 2.3, 3.35, 2.5, { size: 19 });
  });
  [[`${ver.passed}/${ver.total}`, "independent recomputations pass", HEX.lime], ["8 + 5", "Python + dashboard unit tests", HEX.cyan],
    [`${webv.passed}/${webv.total}`, "browser checks (desktop + phone)", HEX.violet]].forEach(([v, l, c], i) => stat(s, 0.6 + i * 4.1, 5.05, 3.9, v, l, c, 30));
}

// M5 · 15. Advisor
pres.addSection({ title: "Decisions" });
{
  const asia = s21.filter((r) => r.asia);
  const s = slide("CONTENT", "Decisions", M[4], "Should you mine in Hong Kong?",
    `Thank you. Now the decision. At our data freeze, one terahash per second earned about ${f(st.hashprice_usd_th_day_30d, 3)} US dollars a day. An Antminer S21 therefore covers its electricity only below ${f(s21be, 3)} dollars per kilowatt-hour. Hong Kong business power costs ${f(hkS21.price_usd_kwh, 3)}, so an S21 here loses ${f(-hkS21.profit_usd_day, 2)} dollars a day. Across Asia, only the economies in green are below break-even. For a 1.2 terahash home device, the advisor's answer is clear: it is a lottery ticket, with odds of ${odds(bitaxe.solo_p_block_per_year)} per year, not an income. Because this is real money, the advisor shows odds and costs, never investment advice.`);
  s.addChart(pres.charts.BAR, [{ name: "Business electricity USD/kWh", labels: asia.map((r) => r.country), values: asia.map((r) => r.price_usd_kwh) }], {
    x: 0.6, y: 1.45, w: 7.4, h: 5.1, barDir: "col", ...chartBase(`Business power (USD/kWh) · break-even ${f(s21be, 3)}`), showLegend: false,
    chartColors: asia.map((r) => (r.country === "Hong Kong" ? HEX.btc : r.price_usd_kwh <= s21be ? HEX.lime : "CFC2AE")),
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", valAxisLabelFormatCode: "0.00", catAxisLabelRotate: -45 });
  card(s, 8.3, 1.45, 4.4, 5.1, { top: HEX.btc });
  kicker(s, "HONG KONG · BUSINESS TARIFF", 8.55, 1.7, 4);
  const rows = adv.filter((a) => a.country === "Hong Kong" && a.tariff === "business");
  rows.forEach((r, i) => {
    T(s, r.device, { x: 8.55, y: 2.2 + i * 0.95, w: 4, h: 0.35, fontSize: 19, bold: true });
    T(s, `${r.profit_usd_day >= 0 ? "+" : "−"}$${f(Math.abs(r.profit_usd_day), 2)}/day · solo ${odds(r.solo_p_block_per_year)}/yr`, { x: 8.55, y: 2.55 + i * 0.95, w: 4, h: 0.55, fontSize: 17, color: r.profit_usd_day >= 0 ? HEX.lime : HEX.red });
  });
}

// M5 · 16. Demo
{
  const s = slide("CONTENT", "Decisions", M[4], "Live demo: the HashAtlas dashboard",
    "[Live demo, 90 seconds; switch to the browser.] One: the Overview, with seventeen years of hash rate, eras and halvings. Two: Block Radar: reveal the labels of blocks mined after our freeze. Three: Fingerprint Lab: load a real solo block, flip the version-rolling feature and watch the tree re-route it. Four: Miner Advisor: switch from Hong Kong to Kazakhstan and watch the verdict change. [If the network fails, use the screenshot on this slide.]", { fixed: 90 });
  card(s, 0.6, 1.45, 8.2, 5.1);
  img(s, ASSET("demo_overview.png"), 0.75, 1.55, 7.9, 4.9);
  const steps = [["1", "Overview", "Hash rate and halvings"], ["2", "Block Radar", "reveal post-freeze blocks"], ["3", "Fingerprint Lab", "Change one feature"], ["4", "Miner Advisor", "Hong Kong → Kazakhstan"]];
  steps.forEach(([k, t, d], i) => {
    hexBadge(s, 9.1, 1.6 + i * 1.12, k, [HEX.violet, HEX.cyan, HEX.magenta, HEX.btc][i], 0.55);
    T(s, t, { x: 9.8, y: 1.6 + i * 1.12, w: 2.9, h: 0.4, fontSize: 20, bold: true });
    T(s, d, { x: 9.8, y: 1.98 + i * 1.12, w: 2.9, h: 0.7, fontSize: 17, color: HEX.text2 });
  });
  T(s, team.live_site.replace("https://", "").replace(/\/$/, ""), { x: 9.1, y: 6.05, w: 3.6, h: 0.45, fontSize: 18, bold: true, color: HEX.btcDeep, hyperlink: { url: team.live_site } });
}

// M5 · 17. Future
{
  const sCase = fu.devices.filter((d) => d.device === "Antminer S21");
  const s = slide("CONTENT", "Decisions", M[4], "What could the 2028 halving change?",
    `How much future did we include? Only what can be grounded. The protocol halves the block subsidy at height one million fifty thousand, and our ${n0(fu.n_paths)} simulated paths put that around ${fu.halving.date_p50}. Hash-rate growth is resampled from history, while price and fees are scenarios the user chooses, not forecasts. We also backtested the method from past dates: the 80 percent band covered ${pc(fu.backtest.summary.coverage_80pct_band)} of cases, but a naive no-growth guess had a smaller median error, so the fan should be read as a range. At today's price, the S21's break-even power price falls from ${f(sCase[0].breakeven_usd_kwh_p50, 3)} in early 2027 to ${f(sCase[1].breakeven_usd_kwh_p50, 3)} a month after the halving. ${M[0]} will close.`);
  card(s, 0.6, 1.45, 8.2, 5.1);
  img(s, FIG("f17_future"), 0.75, 1.55, 7.9, 4.9);
  stat(s, 9.05, 1.45, 3.65, fu.halving.date_p50, "projected halving (median path)", HEX.btcDeep, 28);
  stat(s, 9.05, 3.2, 3.65, pc(fu.backtest.summary.coverage_80pct_band), "backtest: realised value inside the 80% band", HEX.cyan, 30);
  stat(s, 9.05, 4.95, 3.65, `${f(sCase[0].breakeven_usd_kwh_p50, 3)} → ${f(sCase[1].breakeven_usd_kwh_p50, 3)}`, "S21 break-even USD/kWh, 2027 → post-halving", HEX.magenta, 26);
}

// M1 · 18. Conclusion
pres.addSection({ title: "Closing" });
{
  const s = slide("CONTENT", "Closing", M[0], "So, can a small miner still win?",
    `Behaviour narrows down the pool. Weekly patterns recover the hardware eras. And a home miner in Hong Kong faces solo odds of ${odds(bitaxe.solo_p_block_per_year)} a year, while paying for electricity every day. At this tariff, the S21 loses money each day.`);
  const ans = [["Q1", `The true pool appears in the top three for ${pc(TF[op].top3_accuracy)} of blocks`, `Exact pool ${pc(TF[op].accuracy)} (baseline ${pc(TF.majority.accuracy)})`, HEX.violet],
    ["Q2", "Weekly fingerprints recover the hardware eras", `ARI ${f(ward.ari_vs_hardware_eras, 2)} without any hardware labels`, HEX.cyan],
    ["Q3", "A Hong Kong home miner faces long odds", `${odds(bitaxe.solo_p_block_per_year)} per year · S21 break-even ${f(s21be, 3)} USD/kWh vs HK ${f(hkS21.price_usd_kwh, 3)}`, HEX.btcDeep]];
  ans.forEach(([k, t, d, c], i) => {
    card(s, 0.6, 1.5 + i * 1.65, 12.1, 1.45);
    hexBadge(s, 0.9, 1.85 + i * 1.65, k, c === HEX.btcDeep ? HEX.btc : c, 0.75);
    T(s, t, { x: 1.95, y: 1.72 + i * 1.65, w: 10.5, h: 0.55, fontSize: 26, bold: true, italic: true, fontFace: HEAD });
    T(s, d, { x: 1.95, y: 2.3 + i * 1.65, w: 10.5, h: 0.45, fontSize: 19, color: c });
  });
  T(s, `Dashboard ${team.live_site.replace("https://", "").replace(/\/$/, "")}  ·  GitHub: ansonlo-dev/HashAtlas`, { x: 0.6, y: 6.5, w: 12.1, h: 0.4, fontSize: 14, color: HEX.text2 });
}

// The audience can save the video without interrupting the presentation.
{
  const url = "https://www.youtube.com/watch?v=bBC-nXj3Ng4";
  const s = slide("CONTENT", "Closing", M[0], "How does proof of work secure Bitcoin?",
    "For an animated explanation of proof of work, save this 3Blue1Brown video for later. We welcome your questions. [Advance to Q&A.]");
  kicker(s, "FURTHER VIEWING", 0.8, 1.68, 6);
  T(s, "But how does bitcoin\nactually work?", { x: 0.8, y: 2.32, w: 7.8, h: 1.65,
    fontFace: HEAD, fontSize: 44, bold: true, italic: true });
  T(s, "3Blue1Brown", { x: 0.8, y: 4.2, w: 7, h: 0.5, fontSize: 24, color: HEX.text2 });
  T(s, "Watch later on YouTube", { x: 0.8, y: 5.45, w: 6, h: 0.6,
    fontSize: 24, bold: true, color: HEX.btcDeep, hyperlink: { url } });
  img(s, ASSET("bitcoin_video_qr.png"), 8.55, 1.85, 3.8, 3.8);
  T(s, "Scan to save the video", { x: 8.45, y: 5.8, w: 4, h: 0.5, fontSize: 19, align: "center" });
}

// Q&A (not timed)
{
  const s = slide("SECTION", "Closing", "All", "Thank you\u200B",
    "Invite questions; each member answers for their own stage (see the Q&A sheet).", { untimed: true });
  bitcoin(s, 10.2, 3.0, 1.7);
  T(s, "HASHATLAS", { x: 0.8, y: 1.9, w: 6, h: 0.5, fontSize: 18, bold: true, color: HEX.btc, charSpacing: 8 });
  T(s, team.members.map((m) => `${m.name}${m.captain ? " (captain)" : ""}  ·  ${m.short_role}`).join("\n"), { x: 0.8, y: 4.2, w: 10, h: 2.2, fontSize: 20, color: "DED6CA" });
}

// Appendix
pres.addSection({ title: "Appendix" });
{
  const rs = J("artifacts/explanations.json").root_split_worked;
  const kt = cl.kmeans_trace;
  const s = slide("APPENDIX", "Appendix", "", "A1 · Checking Gini and K-means by hand", "Backup for questions on decision-tree impurity and K-means.", { untimed: true });
  card(s, 0.6, 1.4, 6.0, 5.2);
  kicker(s, "ROOT SPLIT (TRAINING TREE)", 0.9, 1.6, 5.4);
  bullets(s, [`test: ${rs.feature} ≤ ${f(rs.threshold, 3)}`, `n = ${n0(rs.n)} → left ${n0(rs.n_left)}, right ${n0(rs.n_right)}`,
    `Gini parent ${f(rs.gini.parent, 4)}; left ${f(rs.gini.left, 4)}; right ${f(rs.gini.right, 4)}`,
    `weighted = (nL·GL + nR·GR)/n = ${f(rs.gini.weighted_children, 4)}`, `Gini reduction ${f(rs.gini.reduction, 4)} · entropy gain ${f(rs.entropy.information_gain, 4)}`], 0.9, 2.15, 5.5, 4.2, { size: 19 });
  card(s, 6.8, 1.4, 5.9, 5.2);
  kicker(s, "K-MEANS, ONE STEP BY HAND", 7.1, 1.6, 5.4, HEX.violet);
  bullets(s, [`K = ${kt.k}, fixed initial centroids`, `SSE after assignment ${f(kt.sse_initial_assignment, 1)}`, `SSE after centroid update ${f(kt.sse_after_update, 1)} (never increases)`,
    `cluster sizes ${kt.sizes_after_first_assignment.join(", ")}`, `max |difference| vs scikit-learn ${kt.max_abs_diff_vs_sklearn_centroids.toExponential(1)}`], 7.1, 2.15, 5.4, 4.2, { size: 19 });
}
{
  const s = slide("APPENDIX", "Appendix", "", "A2 · Apriori, level by level", "Backup: candidate generation and pruning counts, brute-force verification.", { untimed: true });
  const rows = [["k", "joined candidates", "pruned by subset", "counted", "frequent"]].concat(ru.apriori_trace.map((t) => [t.k, n0(t.candidates), n0(t.pruned_by_subset), n0(t.counted), n0(t.frequent)]));
  s.addTable(rows.map((r, i) => r.map((c) => ({ text: String(c), options: { bold: i === 0, color: i === 0 ? "FFFFFF" : HEX.text, fill: { color: i === 0 ? HEX.ink : HEX.card }, align: "center" } }))), {
    x: 0.6, y: 1.5, w: 7.5, fontSize: 19, fontFace: BODY, border: { type: "solid", color: HEX.line, pt: 0.75 }, margin: 0.1 });
  card(s, 8.4, 1.5, 4.3, 3.8);
  kicker(s, "VERIFIED", 8.7, 1.7, 3.8, HEX.lime);
  T(s, `Exhaustive count of all itemsets up to size ${ru.brute_force_check.max_len} over ${ru.brute_force_check.items_checked} items: ${ru.brute_force_check.frequent_by_brute_force} frequent, ${ru.brute_force_check.missing_from_apriori} missing, ${ru.brute_force_check.wrong_counts} wrong counts.`, { x: 8.7, y: 2.2, w: 3.8, h: 2.7, fontSize: 20, color: HEX.text });
  T(s, `min support ${pc(ru.min_support)} (${n0(ru.min_count)} blocks) · min confidence ${pc(ru.min_confidence)} · lift = confidence ÷ base rate`, { x: 0.6, y: 5.8, w: 12, h: 0.7, fontSize: 19, color: HEX.text2 });
}
{
  const pcl = models.test.per_class;
  const s = slide("APPENDIX", "Appendix", "", "A3 · Per-class scorecard (sealed test)", "Backup: precision, recall and F1 for every class.", { untimed: true });
  const rows = [["class", "precision", "recall", "F1", "blocks"]].concat(Object.entries(pcl).map(([k, v]) => [k, f(v.precision, 2), f(v.recall, 2), f(v["f1-score"], 2), n0(v.support)]));
  s.addTable(rows.map((r, i) => r.map((c, j) => ({ text: String(c), options: { bold: i === 0, color: i === 0 ? "FFFFFF" : HEX.text, fill: { color: i === 0 ? HEX.ink : HEX.card }, align: j ? "right" : "left" } }))), {
    x: 0.6, y: 1.4, w: 12.1, colW: [4.1, 2, 2, 2, 2], fontSize: 18, fontFace: BODY, border: { type: "solid", color: HEX.line, pt: 0.75 }, margin: 0.06 });
}
{
  const s = slide("APPENDIX", "Appendix", "", "A4 · Task Division\u200B", "Backup: member contributions (also in report section 17).", { untimed: true });
  team.members.forEach((m, i) => {
    card(s, 0.6, 1.35 + i * 1.08, 12.1, 0.95);
    T(s, m.name + (m.captain ? " (captain)" : ""), { x: 0.85, y: 1.45 + i * 1.08, w: 2.7, h: 0.4, fontSize: 15, bold: true, color: HEX.btcDeep });
    T(s, m.student_id, { x: 0.85, y: 1.83 + i * 1.08, w: 2.7, h: 0.4, fontSize: 16, color: HEX.text2 });
    T(s, m.short.join("  ·  "), { x: 3.7, y: 1.45 + i * 1.08, w: 8.9, h: 0.72, fontSize: 18 });

  });
}
{
  const s = slide("APPENDIX", "Appendix", "", "A5 · Declaration of Use of AI-agent", "", { untimed: true });
  const names = `${M.slice(0, -1).join(", ")} and ${M.at(-1)}`;
  const declaration = `We, ${names}, declare that generative artificial intelligence (GAI) tools were used to prepare the submitted work for CDS3004 Data Mining at Lingnan University (2026/27 Term 1), Group D’s HashAtlas group project.`;
  const use = "Claude Code helped explore project alternatives and generated initial code for data preparation and modelling. Parts of the dashboard, report and slides also incorporate agent-generated or agent-revised material. OpenAI Codex helped revise the deliverables and drafted this declaration. Microsoft Edge neural text-to-speech generated the video narration.";
  const review = "The team selected the Bitcoin topic and takes responsibility for the methods, evidence, attribution and conclusions. Project verification included checking for missing block heights, revising rule thresholds after an empty run and backtesting the Future Lab method.";

  T(s, declaration, { x: 0.6, y: 1.42, w: 12.1, h: 1.18, fontSize: 18 });
  const panels = [["Use of tools and outputs", use], ["Review and responsibility", review]];
  panels.forEach(([heading, body], i) => {
    const x = 0.6 + 6.2 * i;
    card(s, x, 2.78, 5.9, 3.42);
    T(s, heading, { x: x + 0.25, y: 3.01, w: 5.4, h: 0.42, fontSize: 20, bold: true, color: HEX.btcDeep });
    T(s, body, { x: x + 0.25, y: 3.53, w: 5.4, h: 2.39, fontSize: 17, color: HEX.text2 });
  });

  const repo = "https://github.com/ansonlo-dev/HashAtlas";
  const link = (text, url) => ({ text, options: { hyperlink: { url }, color: HEX.btcDeep } });
  T(s, [
    link("Report §15 and §18", `${repo}/blob/main/reports/technical_report.md#15-declaration-of-use-of-ai-agent`),
    { text: "   ·   " },
    link("Agent-use trajectory index", `${repo}/tree/main/agent_trajectories`),
    { text: "   ·   " },
    link("Lingnan University GAI guidelines §2", "https://www.ln.edu.hk/tlc/f/page/107180/326402/Guidelines%20for%20Using%20GAI%20Tools%20%28Oct%202024%29.pdf"),
  ], { x: 0.6, y: 6.48, w: 12.1, h: 0.32, fontSize: 13 });

  s.addNotes(`${declaration}\n\n${use}\n\n${review}\n\nExample prompts, paraphrased: we asked Claude Code to consider solo Bitcoin mining, electricity prices across economies and the GPU and ASIC eras, and to advise on the scope of future analysis. We asked Codex to improve the slides within the existing theme and to draft the declaration against the University guidance. The voice in the introduction video is en-US-SteffanNeural, accessed through edge-tts. Report sections 15 and 18 give the verification examples, tool references and further details. Each member’s own trajectory records their prompts, responses and revisions for submission.`);
}

module.exports = { SCRIPT };

(async () => {
  const out = path.join(__dirname, "..", "HashAtlas.pptx");
  await pres.writeFile({ fileName: out });
  fs.writeFileSync(path.join(__dirname, "theme.json"), JSON.stringify(THEME, null, 1));
  // Use the slide notes for the script and timing sheet too.
  const timed = SCRIPT.filter((r) => r.timed && (r.seconds || r.video));
  const speech = timed.reduce((a, r) => a + r.seconds, 0);
  const video = timed.reduce((a, r) => a + r.video, 0);
  const total = speech + video;
  const mmss = (t) => `${Math.floor(t / 60)}:${String(Math.round(t % 60)).padStart(2, "0")}`;
  const per = {};
  for (const r of timed) per[r.presenter] = (per[r.presenter] || 0) + r.seconds;
  let md = `# HashAtlas presentation script\n\n`;
  md += `**Slot: 20:00 (Q&A not included).** Planned: ${mmss(video)} video + ${mmss(speech)} speaking = **${mmss(total)}**, leaving **${mmss(1200 - total)}** for hand-overs, clicks and the unexpected. `;
  md += `Speaking time = words at ${WPM} wpm + 8 s per slide; the demo is a fixed 90 s slot. Generated from \`presentation/build/build_deck.js\` together with the slides (the same text is in the speaker notes); every number comes from the pipeline outputs.\n\n`;
  md += `| Presenter | Slides | Speaking | Ends by |\n| :--- | :--- | ---: | ---: |\n`;
  let cum = 0;
  const order = [...new Set(timed.map((r) => r.presenter))];
  const ends = {};
  for (const r of timed) { cum += r.seconds + r.video; ends[r.presenter] = cum; }
  for (const p of order) md += `| ${p}${team.members.find((m) => m.name === p)?.captain ? " (captain)" : ""} | ${timed.filter((r) => r.presenter === p).map((r) => r.n).join(", ")} | ${mmss(per[p])} | ${mmss(ends[p])} |\n`;
  md += `| *Video (played, not spoken)* | 2 | ${mmss(video)} | |\n\n`;
  md += `Rehearsal rule: if a presenter runs more than 15 s over their total, cut a sentence from their *own* slides, never from the next person's.\n\n`;
  let csv = "slide,presenter,title,speaking_s,video_s,spoken_words,cumulative_end,actual_rehearsal_s\n";
  cum = 0;
  for (const r of timed) {
    cum += r.seconds + r.video;
    md += `## Slide ${r.n} · ${r.title === "(title)" ? "Introduction video" : r.title}\n\n**${r.presenter}** · ${r.seconds} s speaking${r.video ? ` + ${r.video} s video` : ""} (ends at ${mmss(cum)})\n\n${r.notes}\n\n`;
    csv += `${r.n},${r.presenter},"${(r.title === "(title)" ? "Introduction video" : r.title).replace(/"/g, "'")}",${r.seconds},${r.video},${words(r.notes)},${mmss(cum)},\n`;
  }
  md += `\n**Total: ${mmss(total)} of 20:00.**\n`;
  fs.writeFileSync(path.join(__dirname, "..", "slide_by_slide_script.md"), md);
  fs.writeFileSync(path.join(__dirname, "..", "timing_check.csv"), csv);
  console.log(`wrote HashAtlas.pptx (${SCRIPT.length} slides): video ${video}s + speaking ${speech}s = ${mmss(total)}`);
  for (const p of order) console.log(`  ${p.padEnd(18)} ${mmss(per[p])}`);
})();
