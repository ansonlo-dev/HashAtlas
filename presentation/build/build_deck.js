// Builds presentation/HashAtlas.pptx (and the speaker script) from the pipeline outputs.
// Run: cd presentation/build && node build_deck.js   (then ./make.sh applies the theme, validates and renders the PDF)
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
const FIG = (n) => path.join(ROOT, "reports", "figures", "dark", `${n}.png`);
const SHOT = (n) => path.join(ROOT, "reports", "screenshots", `${n}.png`);
const ASSET = (n) => path.join(__dirname, "..", "assets", n);

// formatting
const n0 = (x) => Math.round(x).toLocaleString("en-US");
const f = (x, d = 2) => (x == null ? "n/a" : Number(x).toFixed(d));
const pc = (x, d = 0) => (x == null ? "n/a" : `${(100 * x).toFixed(d)}%`);
const odds = (p) => (!p ? "n/a" : p >= 0.2 ? pc(p, 0) : `1 in ${n0(1 / p)}`);

// theme (structured deck)
const THEME = {
  name: "HashAtlas Neon", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "070A1A", lt1: "FFFFFF", dk2: "1A2150", lt2: "EAF0FF", accent1: "F7931A", accent2: "A78BFA",
    accent3: "22D3EE", accent4: "F472B6", accent5: "A3E635", accent6: "60A5FA", hlink: "22D3EE", folHlink: "A78BFA" },
};
const HEX = { bg: "070A1A", card: "111633", card2: "161C40", line: "2A3270", text: "EAF0FF", text2: "B9C2E6", muted: "8790B8",
  btc: "F7931A", violet: "A78BFA", cyan: "22D3EE", magenta: "F472B6", lime: "A3E635", blue: "60A5FA", red: "FB7185" };
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "HashAtlas: Can a Small Bitcoin Miner Still Win?";
pres.author = `Team ${team.team_name}`;
pres.subject = "CDS3004 Data Mining group project presentation";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const SC = pres.SchemeColor;

pres.defineSlideMaster({
  title: "TITLE", background: { path: ASSET("bg_title.png") },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.0, w: 11.7, h: 2.1, fontSize: 48, bold: true, color: SC.background1, valign: "top", align: "left", margin: 0 }, text: "" } }],
});
pres.defineSlideMaster({
  title: "SECTION", background: { path: ASSET("bg_section.png") },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.6, w: 11.7, h: 1.4, fontSize: 44, bold: true, color: SC.background1, valign: "top", align: "left", margin: 0 }, text: "" } }],
});
pres.defineSlideMaster({
  title: "CONTENT", background: { path: ASSET("bg_content.png") },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.9, fontSize: 32, bold: true, color: SC.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
    { text: { text: "HASHATLAS  ·  CDS3004 DATA MINING", options: { x: 0.6, y: 7.02, w: 6, h: 0.3, fontSize: 10, color: "8790B8", charSpacing: 2, margin: 0 } } },
  ],
  slideNumber: { x: 12.25, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: "8790B8", align: "right" },
});
pres.defineSlideMaster({
  title: "APPENDIX", background: { path: ASSET("bg_content.png") },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.8, fontSize: 28, bold: true, color: SC.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
    { text: { text: "APPENDIX  ·  backup for questions", options: { x: 0.6, y: 7.02, w: 6, h: 0.3, fontSize: 10, color: "8790B8", charSpacing: 2, margin: 0 } } },
  ],
  slideNumber: { x: 12.25, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: "8790B8", align: "right" },
});

// helpers
const T = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, color: SC.background2, valign: "top", align: "left", fontSize: 16, ...o });
function card(s, x, y, w, h, o = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: o.fill ?? HEX.card, transparency: o.tr ?? 15 },
    line: { color: o.line ?? HEX.line, width: 1 }, objectName: o.name ?? "card",
    shadow: { type: "outer", color: "000000", opacity: 0.35, blur: 10, offset: 3, angle: 90 } });
}
function hexBadge(s, x, y, label, color = HEX.btc, d = 0.62) {
  s.addShape(pres.shapes.HEXAGON, { x, y, w: d, h: d * 0.9, fill: { color: HEX.bg }, line: { color, width: 2 }, objectName: `badge ${label}` });
  T(s, label, { x, y: y + 0.02, w: d, h: d * 0.86, fontSize: 15, bold: true, color, align: "center", valign: "middle" });
}
function stat(s, x, y, w, value, label, color = HEX.btc, size = 40) {
  card(s, x, y, w, 1.6);
  T(s, value, { x: x + 0.25, y: y + 0.18, w: w - 0.5, h: 0.8, fontSize: size, bold: true, color, fit: "shrink" });
  T(s, label, { x: x + 0.25, y: y + 1.0, w: w - 0.5, h: 0.5, fontSize: 13, color: HEX.text2 });
}
function img(s, file, x, y, w, h) {
  if (!fs.existsSync(file)) { T(s, `[missing ${path.basename(file)}]`, { x, y, w, h, color: HEX.red }); return; }
  const { w: pw, h: ph } = pngSize(file);
  const r = Math.min(w / pw, h / ph);
  const W = pw * r, H = ph * r;
  s.addImage({ path: file, x: x + (w - W) / 2, y: y + (h - H) / 2, w: W, h: H, altText: path.basename(file) });
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
        bullet: { code: "25C6", indent: 18 }, breakLine: j === parts.length - 1 && i < items.length - 1, paraSpaceAfter: 6 } }));
  }).flat(), { isTextBox: true, x, y, w, h, fontSize: o.size ?? 16, valign: "top", margin: 0, color: HEX.text });
}
const chartBase = (title) => ({
  showTitle: !!title, title, titleColor: HEX.text, titleFontSize: 13, titleFontFace: "+mn-lt",
  catAxisLabelColor: HEX.text2, valAxisLabelColor: HEX.muted, catAxisLabelFontSize: 11, valAxisLabelFontSize: 10,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", valGridLine: { color: "1F2547", size: 0.75 }, catGridLine: { style: "none" },
  catAxisLineShow: false, valAxisLineShow: false, legendColor: HEX.text2, legendFontSize: 11, legendFontFace: "+mn-lt",
  dataLabelColor: HEX.text, dataLabelFontSize: 10, dataLabelFontFace: "+mn-lt",
});

const SCRIPT = [];
let secSeconds = 0;
const WPM = 130;
const words = (t) => (t || "").split(/\s+/).filter(Boolean).length;
function slide(master, section, presenter, title, seconds, notes) {
  // Speaking time follows the script: words at 130 wpm + 8 s for pointing/transition (demo and Q&A keep fixed slots)
  if (seconds && seconds < 100 && master !== "SECTION") seconds = Math.round(words(notes) / WPM * 60 + 8);
  const s = pres.addSlide({ masterName: master, sectionTitle: section });
  if (title) s.addText(title, { placeholder: "title" });
  if (notes) s.addNotes(`${presenter ? presenter + " · " : ""}${seconds ? `~${seconds}s · ` : ""}${notes}`);
  SCRIPT.push({ n: SCRIPT.length + 1, section, presenter, title: title || "(title)", seconds, notes });
  secSeconds += seconds || 0;
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

// 1. Title
pres.addSection({ title: "Opening" });
{
  const s = slide("TITLE", "Opening", M[0], "Can a small Bitcoin miner still win?", 35,
    `Good morning. Imagine you buy a small mining device the size of a paperback, plug it in at home in Hong Kong, and hope to win a whole Bitcoin block — about ${f(fu.subsidy_now_btc ?? 3.125, 3)} bitcoin plus fees. Is that a dream, a lottery, or a business? We are Team HashAtlas, and we mined the complete history of Bitcoin — ${n0(q.rows_loaded)} blocks — to find out.`);
  T(s, "HASHATLAS", { x: 0.8, y: 1.25, w: 8, h: 0.6, fontSize: 20, bold: true, color: HEX.btc, charSpacing: 8 });
  T(s, `Mining ${n0(q.rows_loaded)} Bitcoin blocks for miner fingerprints, mining eras, pool families — and what a miner in Asia should do`, { x: 0.8, y: 4.15, w: 10.5, h: 0.9, fontSize: 20, color: HEX.text2 });
  T(s, `${M.join("  ·  ")}`, { x: 0.8, y: 5.55, w: 11.5, h: 0.4, fontSize: 15, color: HEX.text });
  T(s, `CDS3004 Data Mining  ·  Lingnan University  ·  CRN ${team.crn}  ·  live dashboard ${team.live_site.replace("https://", "")}`, { x: 0.8, y: 6.0, w: 11.5, h: 0.4, fontSize: 13, color: HEX.muted });
}

// 2. Hook
{
  const s = slide("CONTENT", "Opening", M[0], "The lottery that still pays out", 55,
    `In 2009 a laptop won blocks every day. Today a 1.2 terahash home miner — the most popular hobby device — has odds of about ${odds(dec.advisor.find((a) => a.device.startsWith("Bitaxe")).solo_p_block_per_year)} per year. And yet solo miners still win: ${recentSolo["2025"] ?? 0} blocks in 2025 and ${recentSolo["2026"] ?? 0} so far in 2026 went to solo-mining services. So we asked three data-mining questions: can we tell who mined a block from its behaviour alone; do the data rediscover the history of mining; and what should a miner in Hong Kong or Asia actually do — today and after the 2028 halving?`);
  stat(s, 0.6, 1.5, 3.9, odds(dec.advisor.find((a) => a.device.startsWith("Bitaxe")).solo_p_block_per_year), "chance per year that a 1.2 TH/s home miner wins a block", HEX.magenta, 40);
  stat(s, 4.7, 1.5, 3.9, `${recentSolo["2025"] ?? 0} + ${recentSolo["2026"] ?? 0}`, "blocks still won by solo miners in 2025 + 2026", HEX.btc, 40);
  stat(s, 8.8, 1.5, 3.9, `${f(st.hashrate_ths_30d / 1e6, 0)} EH/s`, "network hash rate at our data freeze (31 Oct 2026)", HEX.cyan, 40);
  const qs = [["Q1", "CLASSIFY", "From a block's behavioural fingerprint alone, who mined it — a pool or a solo miner?", HEX.violet],
    ["Q2", "CLUSTER + RULES", "Do the data rediscover the CPU → GPU → ASIC eras? Which pools build blocks alike?", HEX.cyan],
    ["Q3", "DECIDE", "Pool, solo lottery, or switch off — by device, country electricity price and the 2028 halving?", HEX.btc]];
  qs.forEach(([k, t, d, c], i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 3.5, 3.9, 2.9);
    hexBadge(s, x + 0.3, 3.75, k, c);
    T(s, t, { x: x + 1.1, y: 3.85, w: 2.6, h: 0.45, fontSize: 15, bold: true, color: c, charSpacing: 2 });
    T(s, d, { x: x + 0.3, y: 4.6, w: 3.3, h: 1.6, fontSize: 16, color: HEX.text });
  });
}

// 3. Problem
{
  const s = slide("CONTENT", "Opening", M[0], "Problem, constraints and the alternatives we rejected", 60,
    "Our users are a would-be miner in Asia, and analysts who ask how decentralised mining really is. Five constraints shaped the design. First, labels are self-declared: the miner's name comes from text they write in the block, so that text is the label and must never be an input. Second, no look-ahead: pools appear and disappear, so we train on the past and test on the most recent period. Third, solo blocks are extremely rare. Fourth, free data sources are rate-limited. Fifth, we give odds and costs, not investment advice. We rejected price prediction, simple tag lookup, transaction-level tracing and black-box deep learning — the last two for scale, privacy and interpretability.");
  card(s, 0.6, 1.5, 5.9, 4.9);
  T(s, "CONSTRAINTS", { x: 0.9, y: 1.7, w: 5, h: 0.4, fontSize: 14, bold: true, color: HEX.btc, charSpacing: 3 });
  bullets(s, [[{ text: "Self-declared labels", bold: true }, " — the coinbase tag is the label, never a feature"],
    [{ text: "No look-ahead", bold: true }, " — train 2019-23, validate 2024-25Q1, sealed test 2025Q2-26"],
    [{ text: "Extreme imbalance", bold: true }, ` — only ${soloYears} solo blocks in 17 years`],
    [{ text: "Rate-limited sources", bold: true }, " — resumable, hashed, audited acquisition"],
    [{ text: "Ethics", bold: true }, " — pseudonymous data; odds, not financial advice"]], 0.9, 2.2, 5.4, 4, { size: 16 });
  card(s, 6.8, 1.5, 5.9, 4.9);
  T(s, "ALTERNATIVES CONSIDERED", { x: 7.1, y: 1.7, w: 5.3, h: 0.4, fontSize: 14, bold: true, color: HEX.violet, charSpacing: 3 });
  const alts = [["Predict the BTC price", "not about mining; driven by outside events"], ["Look up the coinbase tag", "that is the label — fails when tags are missing"],
    ["Trace transactions", "billions of rows; re-identification risk"], ["Deep learning on raw bytes", "uninterpretable; outside course scope"]];
  alts.forEach(([a, b], i) => {
    T(s, "✕", { x: 7.1, y: 2.3 + i * 0.95, w: 0.4, h: 0.4, fontSize: 18, bold: true, color: HEX.red });
    T(s, a, { x: 7.55, y: 2.27 + i * 0.95, w: 4.9, h: 0.4, fontSize: 16, bold: true, color: HEX.text });
    T(s, b, { x: 7.55, y: 2.65 + i * 0.95, w: 4.9, h: 0.4, fontSize: 14, color: HEX.text2 });
  });
}

// 4. Data
pres.addSection({ title: "Data" });
{
  const s = slide("CONTENT", "Data", M[0], `${n0(q.rows_loaded)} blocks, zero gaps, audited labels`, 70,
    `We collected every block ever mined: the 2009-to-2018 history from Blockchair's daily dumps, and — after their free quota ran out mid-download — everything from 2019 directly from mempool.space, one mining pool at a time, about ${n0(J("artifacts/source_manifest.json").mempool_blocks.calls)} API calls. The final table has no missing and no duplicate heights. Labels need care: we re-applied our own tag-matching labeller to ${n0(q.label_audit.blocks_compared)} blocks that mempool.space had labelled independently. When our labeller finds a tag it is right ${pc(q.label_audit.precision_when_tag_found, 2)} of the time. The chart shows the story in the labels: unattributed miners in the early years, then pools taking over by 2014. Over to ${M[1]} for features.`);
  stat(s, 0.6, 1.45, 2.95, n0(q.rows_loaded), "blocks, heights 0 → " + n0(q.height_range[1]), HEX.btc, 30);
  stat(s, 0.6, 3.2, 2.95, `${q.missing_heights} / ${q.duplicate_heights}`, "missing / duplicate heights", HEX.lime, 30);
  stat(s, 0.6, 4.95, 2.95, pc(q.label_audit.precision_when_tag_found, 2), `label precision vs mempool.space (${n0(q.label_audit.blocks_compared)} blocks)`, HEX.cyan, 30);
  card(s, 3.8, 1.45, 8.9, 5.1);
  img(s, FIG("f02_who_mines"), 3.95, 1.6, 8.6, 4.8);
}

// 5. Features
pres.addSection({ title: "Features & models" });
{
  const s = slide("CONTENT", "Features & models", M[1], "Fingerprints from behaviour, never from the name", 70,
    "A block header contains a 32-bit version field and a 32-bit nonce. They are stored as integers, but they are nominal bit fields — so we decomposed them into bits. Modern ASICs roll the general-purpose version bits 13 to 28, and pools differ in how many bits they roll. From the block body we built ratios like fullness and witness share, and day-relative features: each block's fee level or size minus that day's median, which removes market conditions and leaves the miner's policy. We deliberately added the hour of day as a control feature that should be useless. And we excluded everything that leaks the label: coinbase text, payout address, height and calendar time.");
  const cols = [["HEADER", HEX.violet, ["version → 16 rolling bits, rolled-bit count, signal bits", "nonce → 32 binary bits", "timestamp → offset vs median-of-11, interval"]],
    ["BODY", HEX.cyan, ["fullness = weight / 4M", "witness share, inputs vs outputs", "fee rate, fee percentiles (log1p)"]],
    ["DAY-RELATIVE", HEX.btc, ["fee rate − day median", "tx count − day median", "fullness − day median"]]];
  cols.forEach(([t, c, items], i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.5, 3.9, 3.2);
    T(s, t, { x: x + 0.3, y: 1.7, w: 3.3, h: 0.4, fontSize: 15, bold: true, color: c, charSpacing: 3 });
    bullets(s, items, x + 0.3, 2.25, 3.4, 2.4, { size: 15 });
  });
  card(s, 0.6, 4.95, 6.0, 1.6, { line: HEX.red });
  T(s, "EXCLUDED (LEAKAGE)", { x: 0.9, y: 5.1, w: 5.4, h: 0.4, fontSize: 14, bold: true, color: HEX.red, charSpacing: 3 });
  T(s, "coinbase text · payout address · Blockchair miner guess · height · calendar time · difficulty", { x: 0.9, y: 5.55, w: 5.5, h: 0.9, fontSize: 15, color: HEX.text });
  card(s, 6.8, 4.95, 5.9, 1.6, { line: HEX.lime });
  T(s, "CONTROL FEATURE", { x: 7.1, y: 5.1, w: 5.4, h: 0.4, fontSize: 14, bold: true, color: HEX.lime, charSpacing: 3 });
  T(s, "hour of day (sin, cos): blocks are found at random times, so selection should — and did — remove it", { x: 7.1, y: 5.55, w: 5.4, h: 0.9, fontSize: 15, color: HEX.text });
}

// 6. Selection
{
  const g = fsel.group_ablation.groups;
  const s = slide("CONTENT", "Features & models", M[1], `Feature selection: ${fsel.candidates} → ${fsel.n_selected}`, 60,
    `Selection used training data only, from filter to wrapper. Mutual information was compared with ten random noise probes: anything no better than noise was dropped — ${fsel.removed_mi_below_noise.length} features, including both timestamp features. That is a finding: block discovery is a random process for every miner, so timing carries no fingerprint. Then we removed redundant pairs with Spearman correlation, and finally ran a group ablation: removing the version bits or the body-composition group clearly hurts the cross-validated score, while the hour-of-day control does nothing and was removed.`);
  const steps = [[fsel.candidates, "candidates"], [fsel.candidates - fsel.removed_low_variance.length, "after variance filter"],
    [fsel.candidates - fsel.removed_low_variance.length - fsel.removed_mi_below_noise.length, "MI above noise probes"],
    [fsel.candidates - fsel.removed_low_variance.length - fsel.removed_mi_below_noise.length - fsel.removed_redundant.length, "non-redundant (|ρ| ≤ 0.9)"],
    [fsel.n_selected, "after group ablation"]];
  steps.forEach(([v, l], i) => {
    const w = 5.2 - i * 0.55;
    const x = 0.6 + (5.2 - w) / 2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.55 + i * 1.0, w, h: 0.82, rectRadius: 0.1, fill: { color: [HEX.violet, HEX.blue, HEX.cyan, HEX.magenta, HEX.btc][i], transparency: 70 },
      line: { color: [HEX.violet, HEX.blue, HEX.cyan, HEX.magenta, HEX.btc][i], width: 1.5 }, objectName: `funnel ${i}` });
    T(s, `${v}`, { x: x + 0.2, y: 1.62 + i * 1.0, w: 1.2, h: 0.7, fontSize: 26, bold: true, color: HEX.text, valign: "middle" });
    T(s, l, { x: x + 1.35, y: 1.62 + i * 1.0, w: w - 1.5, h: 0.7, fontSize: 15, color: HEX.text, valign: "middle" });
  });
  const names = Object.keys(g);
  s.addChart(pres.charts.BAR, [{ name: "Δ CV macro-F1 when removed", labels: names, values: names.map((k) => g[k].change) }], {
    x: 6.4, y: 1.45, w: 6.3, h: 5.1, barDir: "bar", ...chartBase("Group ablation: change in CV macro-F1 when a group is removed"), showLegend: false, catAxisLabelPos: "low",
    chartColors: [HEX.magenta], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "+0.000;-0.000", valAxisLabelFormatCode: "0.00" });
}

// 7. Validation design
{
  const S = models.search;
  const sp = models.split;
  const s = slide("CONTENT", "Features & models", M[1], "Three models, one honest validation design", 70,
    `Shuffled cross-validation would put blocks from the same day on both sides and overstate accuracy, so folds are grouped by calendar month. We tuned a decision tree, KNN and both linear and RBF SVMs on the 2019-to-2023 training period. Nested cross-validation estimates the whole tuning procedure for the tree at ${f(models.nested_cv.mean, 3)} macro-F1 — no optimism from tuning. The model choice and the solo threshold were frozen on the out-of-time validation period before the sealed test was opened. ${M[2]} will now show the results.`);
  const segs = [["TRAIN", `${sp.train.first.slice(0, 4)}–${sp.train.last.slice(0, 4)}`, `${n0(sp.train.labelled)} blocks`, HEX.violet, 5.0],
    ["VALIDATION", "2024 – 2025Q1", `${n0(sp.validation.labelled)} blocks`, HEX.cyan, 2.6], ["SEALED TEST", "2025Q2 – 2026-10", `${n0(sp.test.labelled)} blocks`, HEX.btc, 3.1],
    ["NEW", "Nov 2026", `${n0(sp.new.labelled)} blocks`, HEX.magenta, 1.4]];
  let x = 0.6;
  segs.forEach(([t, d, nb, c, w]) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.5, w: w - 0.08, h: 1.3, rectRadius: 0.1, fill: { color: c, transparency: 72 }, line: { color: c, width: 1.5 }, objectName: `split ${t}` });
    T(s, t, { x: x + 0.15, y: 1.6, w: w - 0.3, h: 0.35, fontSize: 13, bold: true, color: c, charSpacing: 2 });
    T(s, d, { x: x + 0.15, y: 1.95, w: w - 0.3, h: 0.35, fontSize: 15, bold: true, color: HEX.text });
    T(s, nb, { x: x + 0.15, y: 2.32, w: w - 0.3, h: 0.35, fontSize: 13, color: HEX.text2 });
    x += w;
  });
  const rows = [["Model", "Searched", "Chosen", "CV macro-F1"]].concat(["tree", "knn", "svm_linear", "svm_rbf"].map((k) => [FAM[k],
    { tree: "criterion × depth × leaf size × class weight", knn: "k × weights × Manhattan/Euclidean", svm_linear: "C (balanced classes)", svm_rbf: "C × γ (balanced)" }[k],
    Object.entries(S[k].best_params).map(([a, b]) => `${a.replace("model__", "")}=${b}`).join(", "), `${f(S[k].cv_macro_f1_mean, 3)} ± ${f(S[k].cv_macro_f1_se, 3)}`]));
  s.addTable(rows.map((r, i) => r.map((c) => ({ text: String(c), options: { bold: i === 0, color: i === 0 ? HEX.btc : HEX.text, fill: { color: i === 0 ? HEX.card2 : HEX.card } } }))), {
    x: 0.6, y: 3.15, w: 12.1, colW: [1.9, 4.4, 3.8, 2.0], fontSize: 13, fontFace: "Calibri", border: { type: "solid", color: HEX.line, pt: 0.75 }, margin: 0.08 });
  T(s, `Folds grouped by month · nested CV (5 × 3) for the tree: ${f(models.nested_cv.mean, 3)} ± ${f(models.nested_cv.sd, 3)} · choice frozen ${models.selection.frozen_at.slice(0, 10)} before the test was opened`, { x: 0.6, y: 6.25, w: 12.1, h: 0.5, fontSize: 14, color: HEX.text2 });
}

// 8. Results
pres.addSection({ title: "Results" });
{
  const names = ["tree", "knn", "svm_linear", "svm_rbf", "decision_stump", "stratified_random", "majority"];
  const s = slide("CONTENT", "Results", M[2], "The tree wins — and hits an informative ceiling", 75,
    `On the sealed test period the decision tree is clearly best: macro-F1 ${f(TF[op].macro_f1, 3)}, bootstrap interval ${f(models.test.bootstrap.macro_f1_95ci[0], 2)} to ${f(models.test.bootstrap.macro_f1_95ci[1], 2)}, about ${f(TF[op].macro_f1 / TF.stratified_random.macro_f1, 1)} times the random baseline. KNN and the SVMs struggle: the signal sits in a few discrete bit patterns that tree splits isolate, while distances and kernels dilute them across fifty features — we tried feature subsets and weighting, without success. Now the three accuracies: the exact pool is right ${pc(TF[op].accuracy)} of the time, against ${pc(TF.majority.accuracy)} for always guessing the largest pool; and the true pool is among the tree's top three ${pc(TF[op].top3_accuracy)} of the time. Behaviour narrows a block to a few look-alike pools — because many pools build identical blocks.`);
  s.addChart(pres.charts.BAR, [
    { name: "Sealed test macro-F1", labels: names.map((k) => FAM[k]), values: names.map((k) => TF[k].macro_f1) },
  ], { x: 0.6, y: 1.45, w: 7.2, h: 5.1, barDir: "col", ...chartBase("Sealed-test macro-F1 (identical blocks for every model)"), showLegend: false,
    chartColors: names.map((k) => (k === op ? HEX.btc : ["tree", "knn", "svm_linear", "svm_rbf"].includes(k) ? HEX.violet : "4B5378")),
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", valAxisLabelFormatCode: "0.0", valAxisMinVal: 0 });
  stat(s, 8.1, 1.45, 4.6, pc(TF[op].accuracy), `exact pool (${models.selection.classes.length} classes)`, HEX.violet, 34);
  stat(s, 8.1, 3.2, 4.6, pc(TF[op].top3_accuracy), "true pool among the top 3 candidates", HEX.cyan, 34);
  stat(s, 8.1, 4.95, 4.6, pc(TF.majority.accuracy), "always guessing the largest pool (baseline)", HEX.muted, 34);
}

// 9. Confusion
{
  const top = models.test.newcomer_pools.slice(0, 3);
  const s = slide("CONTENT", "Results", M[2], "Who looks like whom?", 60,
    `The confusion matrix shows where the errors go. Pools with a distinctive habit — for example signalling bits, or an unusual number of rolled version bits — sit on the diagonal. The largest pools blur into each other, because since 2023 almost everyone fills blocks with the same fee-maximising template. A strong test of the idea: pools that did not exist in training. ${top.map((r) => `${r.miner} is predicted as ${r.top_prediction} ${pc(r.top_share)} of the time`).join("; ")}. Modern solo blocks look like pool blocks too: the solo class reaches an average precision of ${f(TF[op].solo_average_precision ?? TF.tree.solo_average_precision, 2)} against a base rate of ${pc(TF.tree.solo_base_rate, 2)}.`);
  card(s, 0.6, 1.45, 6.6, 5.1);
  img(s, FIG("f08_confusion"), 0.75, 1.55, 6.3, 4.9);
  card(s, 7.45, 1.45, 5.25, 5.1);
  T(s, "NEWCOMERS: WHOSE TEMPLATE?", { x: 7.75, y: 1.65, w: 4.8, h: 0.4, fontSize: 14, bold: true, color: HEX.btc, charSpacing: 2 });
  models.test.newcomer_pools.slice(0, 6).forEach((r, i) => {
    T(s, r.miner, { x: 7.75, y: 2.2 + i * 0.62, w: 2.2, h: 0.4, fontSize: 15, bold: true, color: HEX.text });
    T(s, `→ ${r.top_prediction}`, { x: 9.9, y: 2.2 + i * 0.62, w: 1.9, h: 0.4, fontSize: 15, color: HEX.cyan });
    T(s, pc(r.top_share), { x: 11.75, y: 2.2 + i * 0.62, w: 0.8, h: 0.4, fontSize: 15, bold: true, color: HEX.btc, align: "right" });
  });
  T(s, "Pools absent from training, mapped by the frozen model (validation + test blocks)", { x: 7.75, y: 6.0, w: 4.8, h: 0.45, fontSize: 12, color: HEX.muted });
}

// 10. Eras
{
  const s = slide("CONTENT", "Results", M[2], "The data rediscover mining history on their own", 65,
    `Next, clustering. One row per week, nine features describing how blocks were produced — never the dates of the hardware eras. K-means with K chosen by silhouette, four hierarchical linkages and DBSCAN all ran on the same rows. Only afterwards did we compare with documented history: Ward linkage reaches an adjusted Rand index of ${f(ward.ari_vs_hardware_eras, 2)} and K-means ${f(cl.ari_vs_hardware_eras.kmeans, 2)}. Three eras emerge: the hobbyist CPU and GPU years, the FPGA-to-early-ASIC transition, and the industrial era. Ward's first boundary falls two weeks after the documented start of the FPGA era, and its second two days after the 2016 halving — the start of the Antminer S9 years. DBSCAN marks the fast transition weeks as noise: density-based clustering cannot separate eras that blend into each other.`);
  card(s, 0.6, 1.45, 12.1, 3.2);
  img(s, FIG("f13_eras_timeline"), 0.75, 1.55, 11.8, 3.0);
  stat(s, 0.6, 4.95, 2.9, f(ward.ari_vs_hardware_eras, 2), "ARI, Ward vs documented eras", HEX.btc, 34);
  stat(s, 3.65, 4.95, 2.9, f(cl.ari_vs_hardware_eras.kmeans, 2), `ARI, K-means (K = ${cl.k_selected})`, HEX.violet, 34);
  stat(s, 6.7, 4.95, 2.9, f(cl.seed_stability_ari_mean, 2), "K-means stability over seeds", HEX.cyan, 34);
  stat(s, 9.75, 4.95, 2.95, pc(cl.dbscan_selected.noise_share, 1), "weeks DBSCAN calls noise", HEX.magenta, 34);
}

// 11. Families + rules
{
  const s = slide("CONTENT", "Results", M[2], "Pool families and block signatures", 65,
    `Clustering the pools themselves by their average fingerprint gives families: ${multiFam.slice(0, 3).map((g) => g.join(" plus ")).join("; ")}. The classifier agrees: newcomers like SECPOOL and Luxor are mostly read as AntPool, the pool their fingerprints sit closest to. Association rules tell the same story from another angle. Our from-scratch Apriori, checked against brute force, found rules such as ${ru.rules.length ? ru.rules.slice().sort((a, b) => b.lift - a.lift)[0].antecedent.join(" and ") + " implies " + ru.rules.slice().sort((a, b) => b.lift - a.lift)[0].consequent.replace("miner=", "") + " with lift " + f(ru.rules.slice().sort((a, b) => b.lift - a.lift)[0].lift, 0) : "few strong rules"}. Contrast mining inside each pool gives signatures; the biggest pools have none — they build blocks like everybody else. Similar fingerprints suggest shared templates or software; they do not prove common ownership. Over to ${M[3]}.`);
  card(s, 0.6, 1.45, 7.0, 5.1);
  img(s, FIG("f14_pool_dendrogram"), 0.75, 1.55, 6.7, 4.9);
  card(s, 7.85, 1.45, 4.85, 5.1);
  T(s, "SIGNATURES (CONTRAST APRIORI)", { x: 8.1, y: 1.65, w: 4.5, h: 0.4, fontSize: 13, bold: true, color: HEX.btc, charSpacing: 2 });
  sigs.slice(0, 5).forEach((sg, i) => {
    const t = sg.top[0];
    T(s, sg.pool, { x: 8.1, y: 2.15 + i * 0.82, w: 2.6, h: 0.35, fontSize: 15, bold: true, color: HEX.text });
    T(s, `${f(t.ratio, 1)}×`, { x: 11.3, y: 2.15 + i * 0.82, w: 1.2, h: 0.35, fontSize: 15, bold: true, color: HEX.lime, align: "right" });
    T(s, t.itemset.filter((x) => !x.startsWith("fullness")).join(" ∧ ") || t.itemset.join(" ∧ "), { x: 8.1, y: 2.5, w: 4.4, h: 0.4, fontSize: 12, color: HEX.text2, ...{ y: 2.5 + i * 0.82 } });
  });
  T(s, `Apriori: ${n0(ru.transactions)} blocks · ${ru.frequent_itemsets} frequent itemsets · brute-force check ${ru.brute_force_check.passed ? "passed" : "FAILED"}`, { x: 8.1, y: 6.15, w: 4.5, h: 0.35, fontSize: 11, color: HEX.muted });
}

// 12. Advisor
pres.addSection({ title: "Decisions" });
{
  const asia = s21.filter((r) => r.asia);
  const s = slide("CONTENT", "Decisions", M[3], "Should you mine in Hong Kong?", 70,
    `Now the decision. At the freeze, one terahash per second earned about ${f(st.hashprice_usd_th_day_30d, 3)} US dollars a day. An Antminer S21 therefore covers its electricity only below ${f(s21be, 3)} dollars per kilowatt-hour. Hong Kong business power costs ${f(hkS21.price_usd_kwh, 3)}, so an S21 here loses ${f(-hkS21.profit_usd_day, 2)} dollars a day. Across Asia, only the economies in green on the chart are below break-even at retail tariffs. For a 1.2 terahash home device the advisor says: this is a lottery ticket — odds of ${odds(bitaxe.solo_p_block_per_year)} per year — not an income.`);
  s.addChart(pres.charts.BAR, [{ name: "Business electricity USD/kWh", labels: asia.map((r) => r.country), values: asia.map((r) => r.price_usd_kwh) }], {
    x: 0.6, y: 1.45, w: 7.4, h: 5.1, barDir: "col", ...chartBase(`Asian business tariffs vs the S21 break-even (${f(s21be, 3)} USD/kWh)`), showLegend: false,
    chartColors: asia.map((r) => (r.country === "Hong Kong" ? HEX.btc : r.price_usd_kwh <= s21be ? HEX.lime : "4B5378")),
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", valAxisLabelFormatCode: "0.00", catAxisLabelRotate: -45 });
  card(s, 8.3, 1.45, 4.4, 5.1);
  T(s, "HONG KONG · BUSINESS TARIFF", { x: 8.55, y: 1.65, w: 4, h: 0.4, fontSize: 13, bold: true, color: HEX.btc, charSpacing: 2 });
  const rows = adv.filter((a) => a.country === "Hong Kong" && a.tariff === "business");
  rows.forEach((r, i) => {
    T(s, r.device, { x: 8.55, y: 2.15 + i * 0.95, w: 4, h: 0.35, fontSize: 14, bold: true, color: HEX.text });
    T(s, `${r.profit_usd_day >= 0 ? "+" : "−"}$${f(Math.abs(r.profit_usd_day), 2)}/day · solo ${odds(r.solo_p_block_per_year)}/yr`, { x: 8.55, y: 2.5 + i * 0.95, w: 4, h: 0.35, fontSize: 13, color: r.profit_usd_day >= 0 ? HEX.lime : HEX.red });
  });
}

// 13. Demo
{
  const s = slide("CONTENT", "Decisions", M[3], "Live demo: the HashAtlas dashboard", 120,
    "Live demo, about two minutes. One: Mission Control — the hash-rate history with eras and halvings. Two: Block Radar — reveal the labels of blocks mined after our freeze and click a confusion cell. Three: Fingerprint Lab — load a real solo block, flip the version-rolling feature and watch the tree re-route it. Four: Miner Advisor — switch from Hong Kong to Kazakhstan and watch the verdict change. If the network fails, the screenshots on this slide are the fallback.");
  card(s, 0.6, 1.45, 8.2, 5.1);
  img(s, ASSET("demo_overview.png"), 0.75, 1.55, 7.9, 4.9);
  const steps = [["1", "Mission Control", "17 years of hash rate, eras, halvings"], ["2", "Block Radar", "reveal post-freeze blocks; confusion"], ["3", "Fingerprint Lab", "edit a real block, re-route the tree"], ["4", "Miner Advisor", "Hong Kong → Kazakhstan"]];
  steps.forEach(([k, t, d], i) => {
    hexBadge(s, 9.1, 1.6 + i * 1.12, k, [HEX.violet, HEX.cyan, HEX.magenta, HEX.btc][i], 0.55);
    T(s, t, { x: 9.8, y: 1.6 + i * 1.12, w: 2.9, h: 0.4, fontSize: 16, bold: true, color: HEX.text });
    T(s, d, { x: 9.8, y: 1.98 + i * 1.12, w: 2.9, h: 0.4, fontSize: 13, color: HEX.text2 });
  });
  T(s, team.live_site.replace("https://", ""), { x: 9.1, y: 6.05, w: 3.6, h: 0.45, fontSize: 18, bold: true, color: HEX.cyan, hyperlink: { url: team.live_site } });
}

// 14. Future
{
  const sCase = fu.devices.filter((d) => d.device === "Antminer S21");
  const s = slide("CONTENT", "Decisions", M[3], "Future Lab: the 2028 halving, with an honest backtest", 70,
    `How much future did we include? Only what can be grounded. The protocol halves the subsidy at height one million fifty thousand — our ${n0(fu.n_paths)} simulated paths put that around ${fu.halving.date_p50}. Hash-rate growth is resampled from history; price and fees are scenarios the user chooses, not forecasts. And we backtested the method from past dates: the 80 percent band covered ${pc(fu.backtest.summary.coverage_80pct_band)} of cases, but a naive no-growth guess had a smaller median error — so read the fan as a range. At today's price, the S21's break-even power price falls from ${f(sCase[0].breakeven_usd_kwh_p50, 3)} in early 2027 to ${f(sCase[1].breakeven_usd_kwh_p50, 3)} a month after the halving. ${M[4]} will close.`);
  card(s, 0.6, 1.45, 8.2, 5.1);
  img(s, FIG("f17_future"), 0.75, 1.55, 7.9, 4.9);
  stat(s, 9.05, 1.45, 3.65, fu.halving.date_p50, "projected halving (median path)", HEX.btc, 28);
  stat(s, 9.05, 3.2, 3.65, pc(fu.backtest.summary.coverage_80pct_band), "backtest: realised value inside the 80% band", HEX.cyan, 30);
  stat(s, 9.05, 4.95, 3.65, `${f(sCase[0].breakeven_usd_kwh_p50, 3)} → ${f(sCase[1].breakeven_usd_kwh_p50, 3)}`, "S21 break-even USD/kWh, 2027 → post-halving", HEX.magenta, 26);
}

// 15. Ethics + agents
pres.addSection({ title: "Closing" });
{
  const s = slide("CONTENT", "Closing", M[4], "Limits, ethics, and how we checked the agents", 65,
    `Three honest limits: labels are self-declared, fingerprints drift so the model is dated, and the solo class rests on a few dozen blocks. Ethically, the data are public and pseudonymous, but fingerprinting is dual-use, so we publish aggregate findings only, and the advisor shows odds, not advice. We used AI coding agents throughout, but every stage was verified by a person. Some agent outputs were wrong and we caught them: a macro-F1 that counted pools which no longer exist, an association-rule run that returned zero rules because the threshold ignored base rates, and a future method that overshot its own backtest. Our independent verification recomputes ${ver.total} results through separate code paths: ${ver.passed} pass.`);
  const cols = [["LIMITS", HEX.red, ["Labels are self-declared; may be shared", "Fingerprints drift; retrain regularly", `Solo class: ${models.split.test.solo} test blocks`, "Retail tariffs; scenarios, not forecasts"]],
    ["ETHICS", HEX.violet, ["Public, pseudonymous data; no personal data", "Fingerprinting is dual-use: aggregates only", "Odds and costs, not investment advice", "Energy: mining follows cheap power"]],
    ["AGENT CHECKS", HEX.lime, ["Human plan review at every stage", "Macro-F1 over vanished pools: fixed", "Zero-rule Apriori run: thresholds fixed", `Independent verification ${ver.passed}/${ver.total}`]]];
  cols.forEach(([t, c, items], i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.5, 3.9, 3.35);
    T(s, t, { x: x + 0.3, y: 1.7, w: 3.3, h: 0.4, fontSize: 15, bold: true, color: c, charSpacing: 3 });
    bullets(s, items, x + 0.3, 2.3, 3.35, 2.5, { size: 15 });
  });
  const webv = J("reports/web_validation.json");
  [[`${ver.passed}/${ver.total}`, "independent recomputations pass", HEX.lime], ["8 + 5", "Python + dashboard unit tests", HEX.cyan],
    [`${webv.passed}/${webv.total}`, "browser checks (desktop + phone)", HEX.violet]].forEach(([v, l, c], i) => stat(s, 0.6 + i * 4.1, 5.05, 3.9, v, l, c, 30));
}

// 16. Conclusion
{
  const s = slide("CONTENT", "Closing", M[4], "So — can a small miner still win?", 60,
    `To answer our three questions. One: behaviour narrows a block down to a few look-alike pools, not always the exact one — and that ceiling is itself evidence that block building is concentrated in fewer set-ups than pool names suggest. Two: the eras of mining are written in the data. Three: in Hong Kong, a small miner can still win — but only as a lottery, with odds of ${odds(bitaxe.solo_p_block_per_year)} a year, while paying for electricity every day. After the 2028 halving the odds stay, and the economics get harder. Thank you — we are happy to take questions.`);
  const ans = [["Q1", "Behaviour narrows a block to a few look-alike pools", `true pool in the top 3: ${pc(TF[op].top3_accuracy)} · exact pool ${pc(TF[op].accuracy)} (baseline ${pc(TF.majority.accuracy)})`, HEX.violet],
    ["Q2", "The eras of mining are written in the data", `ARI ${f(ward.ari_vs_hardware_eras, 2)} without any hardware labels`, HEX.cyan],
    ["Q3", "In Hong Kong, solo mining is a lottery, not an income", `${odds(bitaxe.solo_p_block_per_year)} per year · S21 break-even ${f(s21be, 3)} USD/kWh vs HK ${f(hkS21.price_usd_kwh, 3)}`, HEX.btc]];
  ans.forEach(([k, t, d, c], i) => {
    card(s, 0.6, 1.5 + i * 1.65, 12.1, 1.45);
    hexBadge(s, 0.9, 1.72 + i * 1.65, k, c, 0.75);
    T(s, t, { x: 1.95, y: 1.68 + i * 1.65, w: 10.5, h: 0.55, fontSize: 22, bold: true, color: HEX.text });
    T(s, d, { x: 1.95, y: 2.25 + i * 1.65, w: 10.5, h: 0.45, fontSize: 16, color: c });
  });
  T(s, `Dashboard ${team.live_site.replace("https://", "")}  ·  code, report and trajectories in our GitHub repository`, { x: 0.6, y: 6.5, w: 12.1, h: 0.4, fontSize: 14, color: HEX.text2 });
}

// 17. Q&A
{
  const s = slide("SECTION", "Closing", M[4], "Thank you · Questions", 15, "Invite questions; each member answers for their own stage (see the Q&A sheet).");
  T(s, "HASHATLAS", { x: 0.8, y: 1.9, w: 6, h: 0.5, fontSize: 18, bold: true, color: HEX.btc, charSpacing: 8 });
  T(s, team.members.map((m) => `${m.name} — ${m.short_role}`).join("\n"), { x: 0.8, y: 4.2, w: 9, h: 2.2, fontSize: 15, color: HEX.text2 });
}

// Appendix
pres.addSection({ title: "Appendix" });
{
  const rs = J("artifacts/explanations.json").root_split_worked;
  const kt = cl.kmeans_trace;
  const s = slide("APPENDIX", "Appendix", "", "A1 · Worked checks: Gini split and one K-means iteration", 0, "Backup for questions on decision-tree impurity and K-means.");
  card(s, 0.6, 1.4, 6.0, 5.2);
  T(s, "ROOT SPLIT (training tree)", { x: 0.9, y: 1.6, w: 5.4, h: 0.4, fontSize: 14, bold: true, color: HEX.btc, charSpacing: 2 });
  bullets(s, [`test: ${rs.feature} ≤ ${f(rs.threshold, 3)}`, `n = ${n0(rs.n)} → left ${n0(rs.n_left)}, right ${n0(rs.n_right)}`,
    `Gini parent ${f(rs.gini.parent, 4)}; left ${f(rs.gini.left, 4)}; right ${f(rs.gini.right, 4)}`,
    `weighted = (nL·GL + nR·GR)/n = ${f(rs.gini.weighted_children, 4)}`, `Gini reduction ${f(rs.gini.reduction, 4)} · entropy gain ${f(rs.entropy.information_gain, 4)}`], 0.9, 2.15, 5.5, 4.2, { size: 15 });
  card(s, 6.8, 1.4, 5.9, 5.2);
  T(s, "K-MEANS, ONE STEP BY HAND", { x: 7.1, y: 1.6, w: 5.4, h: 0.4, fontSize: 14, bold: true, color: HEX.violet, charSpacing: 2 });
  bullets(s, [`K = ${kt.k}, fixed initial centroids`, `SSE after assignment ${f(kt.sse_initial_assignment, 1)}`, `SSE after centroid update ${f(kt.sse_after_update, 1)} (never increases)`,
    `cluster sizes ${kt.sizes_after_first_assignment.join(", ")}`, `max |difference| vs scikit-learn ${kt.max_abs_diff_vs_sklearn_centroids.toExponential(1)}`], 7.1, 2.15, 5.4, 4.2, { size: 15 });
}
{
  const s = slide("APPENDIX", "Appendix", "", "A2 · Apriori, level by level", 0, "Backup: candidate generation and pruning counts, brute-force verification.");
  const rows = [["k", "joined candidates", "pruned by subset", "counted", "frequent"]].concat(ru.apriori_trace.map((t) => [t.k, n0(t.candidates), n0(t.pruned_by_subset), n0(t.counted), n0(t.frequent)]));
  s.addTable(rows.map((r, i) => r.map((c) => ({ text: String(c), options: { bold: i === 0, color: i === 0 ? HEX.btc : HEX.text, fill: { color: i === 0 ? HEX.card2 : HEX.card }, align: "center" } }))), {
    x: 0.6, y: 1.5, w: 7.5, fontSize: 15, fontFace: "Calibri", border: { type: "solid", color: HEX.line, pt: 0.75 }, margin: 0.1 });
  card(s, 8.4, 1.5, 4.3, 3.2);
  T(s, "VERIFIED", { x: 8.7, y: 1.7, w: 3.8, h: 0.4, fontSize: 14, bold: true, color: HEX.lime, charSpacing: 2 });
  T(s, `Exhaustive count of all itemsets up to size ${ru.brute_force_check.max_len} over ${ru.brute_force_check.items_checked} items: ${ru.brute_force_check.frequent_by_brute_force} frequent, ${ru.brute_force_check.missing_from_apriori} missing, ${ru.brute_force_check.wrong_counts} wrong counts.`, { x: 8.7, y: 2.2, w: 3.8, h: 2.3, fontSize: 15, color: HEX.text });
  T(s, `min support ${pc(ru.min_support)} (${n0(ru.min_count)} blocks) · min confidence ${pc(ru.min_confidence)} · lift = confidence ÷ base rate`, { x: 0.6, y: 5.6, w: 12, h: 0.5, fontSize: 14, color: HEX.text2 });
}
{
  const pcl = models.test.per_class;
  const s = slide("APPENDIX", "Appendix", "", "A3 · Per-class scorecard (sealed test)", 0, "Backup: precision, recall and F1 for every class.");
  const rows = [["class", "precision", "recall", "F1", "blocks"]].concat(Object.entries(pcl).map(([k, v]) => [k, f(v.precision, 2), f(v.recall, 2), f(v["f1-score"], 2), n0(v.support)]));
  s.addTable(rows.map((r, i) => r.map((c, j) => ({ text: String(c), options: { bold: i === 0, color: i === 0 ? HEX.btc : HEX.text, fill: { color: i === 0 ? HEX.card2 : HEX.card }, align: j ? "right" : "left" } }))), {
    x: 0.6, y: 1.4, w: 8.0, colW: [3.2, 1.2, 1.2, 1.2, 1.2], fontSize: 13, fontFace: "Calibri", border: { type: "solid", color: HEX.line, pt: 0.75 }, margin: 0.06 });
}
{
  const s = slide("APPENDIX", "Appendix", "", "A4 · Who did what", 0, "Backup: member contributions (also in report section 17).");
  team.members.forEach((m, i) => {
    card(s, 0.6, 1.35 + i * 1.08, 12.1, 0.95);
    T(s, m.name, { x: 0.85, y: 1.45 + i * 1.08, w: 2.4, h: 0.4, fontSize: 15, bold: true, color: HEX.btc });
    T(s, m.role, { x: 0.85, y: 1.83 + i * 1.08, w: 2.6, h: 0.4, fontSize: 11, color: HEX.text2 });
    T(s, m.short.join("  ·  "), { x: 3.6, y: 1.55 + i * 1.08, w: 9, h: 0.5, fontSize: 14, color: HEX.text });
  });
}

module.exports = { SCRIPT };

(async () => {
  const out = path.join(__dirname, "..", "HashAtlas.pptx");
  await pres.writeFile({ fileName: out });
  fs.writeFileSync(path.join(__dirname, "theme.json"), JSON.stringify(THEME, null, 1));
  // Speaker script and timing (the same notes as in the .pptx)
  const total = SCRIPT.reduce((a, r) => a + (r.seconds || 0), 0);
  let md = `# HashAtlas presentation script\n\nAbout ${Math.round(total / 60)}-minute group presentation (${Math.floor(total / 60)} min ${total % 60} s), five presenters, including a 2-minute live demo. Timing = spoken words at ${WPM} wpm + 8 s per slide for pointing and hand-overs. Generated from \`presentation/build/build_deck.js\` together with the slides (the same text is in the speaker notes); numbers come from the pipeline outputs.\n\n`;
  let csv = "slide,presenter,title,allocated_s,spoken_words,speech_s_at_130wpm,actual_rehearsal_s\n";
  let cum = 0;
  for (const r of SCRIPT) {
    if (!r.seconds) continue;
    cum += r.seconds;
    md += `## Slide ${r.n} · ${r.title}\n\n**${r.presenter}** · ${r.seconds} s (ends at ${Math.floor(cum / 60)}:${String(cum % 60).padStart(2, "0")})\n\n${r.notes}\n\n`;
    csv += `${r.n},${r.presenter},"${r.title.replace(/"/g, "'")}",${r.seconds},${words(r.notes)},${Math.round(words(r.notes) / WPM * 60)},\n`;
  }
  md += `\n**Total: ${Math.floor(cum / 60)} min ${cum % 60} s.**\n`;
  fs.writeFileSync(path.join(__dirname, "..", "slide_by_slide_script.md"), md);
  fs.writeFileSync(path.join(__dirname, "..", "timing_check.csv"), csv);
  console.log(`wrote HashAtlas.pptx (${SCRIPT.length} slides), script total ${cum}s`);
})();
