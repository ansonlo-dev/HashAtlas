// Validates web/public/data/*.json against the fields the dashboard reads (run: bun run validate-data).
import { readFileSync } from "node:fs";
import { join } from "node:path";

const dir = join(import.meta.dir, "..", "public", "data");
const read = (n: string) => JSON.parse(readFileSync(join(dir, `${n}.json`), "utf8"));
const need: Record<string, string[]> = {
  meta: ["counts.blocks", "headline.macro_f1_test", "headline.nakamoto", "freeze_day", "team.members"],
  models: ["test.confusion.matrix", "test.families.tree.macro_f1", "selection.features", "feature_selection.selected", "nested_cv.mean"],
  tree: ["tree.nodes", "examples", "feature_ranges", "root_split.gini.reduction"],
  radar: ["test_tail", "new_blocks.examples", "unknown_attribution.unknown_share"],
  clusters: ["elbow", "profiles", "hierarchical.ward.cophenetic_correlation", "pool_families.average_dendrogram.icoord"],
  rules: ["rules", "apriori_trace", "brute_force_check.passed", "solo_contrast.itemsets"],
  advisor: ["network.hashrate_ths_30d", "electricity", "devices"],
  future: ["halving.date_p50", "client.h_ths.p50", "backtest.summary.coverage_80pct_band"],
  quality: ["report.label_audit.agreement", "dictionary"],
};
let bad = 0;
for (const [file, paths] of Object.entries(need)) {
  const j = read(file);
  for (const p of paths) {
    const v = p.split(".").reduce((o: any, k) => (o == null ? undefined : o[k]), j);
    if (v === undefined || v === null || (Array.isArray(v) && v.length === 0)) { console.log(`FAIL ${file}.${p}`); bad++; }
  }
}
const tl = read("timeline");
if (!Array.isArray(tl) || tl.length < 800) { console.log("FAIL timeline rows"); bad++; }
const tree = read("tree").tree;
const ids = new Set(tree.nodes.map((n: any) => n.id));
for (const n of tree.nodes) if (!n.leaf && (!ids.has(n.left) || !ids.has(n.right))) { console.log(`FAIL tree node ${n.id} child missing`); bad++; break; }
console.log(bad ? `${bad} problems` : "web data valid");
process.exit(bad ? 1 : 0);
