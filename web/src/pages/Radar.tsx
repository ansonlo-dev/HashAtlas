import { useMemo, useState } from "react";
import { C, EChart, PALETTE, axis, glowLine, legend, tooltip } from "../components/EChart";
import { Err, Kpi, Loading, PageHead, Panel, Seg } from "../components/ui";
import { useData, type Dict } from "../lib/data";
import { fmt, int, pct } from "../lib/format";

const FAM: Record<string, string> = { tree: "Decision tree", knn: "KNN", svm_linear: "Linear SVM", svm_rbf: "RBF SVM",
  decision_stump: "Stump", stratified_random: "Random", majority: "Majority" };

export default function Radar() {
  const { data, error } = useData<{ models: Dict; radar: Dict }>(["models", "radar"]);
  const [reveal, setReveal] = useState(false);
  const [norm, setNorm] = useState<"recall" | "count">("recall");
  const [cell, setCell] = useState<[string, string] | null>(null);

  const charts = useMemo(() => {
    if (!data) return null;
    const t = data.models.test, s = data.models.search;
    const labels: string[] = t.confusion.labels;
    const M: number[][] = t.confusion.matrix;
    const cells: [number, number, number][] = [];
    M.forEach((row, i) => {
      const tot = row.reduce((a, b) => a + b, 0) || 1;
      row.forEach((v, j) => cells.push([j, i, norm === "recall" ? v / tot : v]));
    });
    const max = norm === "recall" ? 1 : Math.max(...cells.map((c) => c[2]));
    const confOpt = {
      tooltip: { ...tooltip({ trigger: "item" }), formatter: (p: Dict) => `true <b>${labels[p.value[1]]}</b><br/>predicted <b>${labels[p.value[0]]}</b><br/>${norm === "recall" ? pct(p.value[2], 1) : int(p.value[2])}` },
      grid: { left: 110, right: 20, top: 10, bottom: 100 },
      xAxis: { type: "category", data: labels, name: "predicted", nameLocation: "middle", nameGap: 82, ...axis({ axisLabel: { color: C.muted, rotate: 50, fontSize: 10.5 } }) },
      yAxis: { type: "category", data: labels, inverse: true, ...axis({ axisLabel: { color: C.muted, fontSize: 10.5 } }) },
      visualMap: { min: 0, max, show: false, inRange: { color: ["#fbf6ee", "#f9d9a8", "#f7931a", "#a65400", "#3b2410"] } },
      series: [{ type: "heatmap", data: cells, itemStyle: { borderColor: "#fffdf9", borderWidth: 1.5, borderRadius: 3 },
        label: { show: true, fontSize: 9.5, rich: { d: { color: "#4a453f", fontSize: 9.5 }, l: { color: "#fff", fontSize: 9.5, fontWeight: 600 } },
          formatter: (p: Dict) => {
            const t = norm === "recall" ? (p.value[2] >= 0.05 ? fmt(p.value[2], 2) : "") : p.value[2] > 0 ? int(p.value[2]) : "";
            return t ? `{${p.value[2] / max > 0.45 ? "l" : "d"}|${t}}` : "";
          } },
        emphasis: { itemStyle: { borderColor: C.text, borderWidth: 2 } } }],
    };
    const names = ["tree", "knn", "svm_linear", "svm_rbf", "decision_stump", "stratified_random", "majority"];
    const cmpOpt = {
      tooltip: tooltip({ valueFormatter: (v: number) => fmt(v, 3) }), legend: legend({ top: 0 }),
      grid: { left: 44, right: 10, top: 34, bottom: 56 },
      xAxis: { type: "category", data: names.map((n) => FAM[n]), ...axis({ axisLabel: { color: C.muted, fontSize: 10, interval: 0, rotate: 30 } }) },
      yAxis: { type: "value", name: "macro-F1", ...axis() },
      series: [
        { name: "CV (2019–23)", type: "bar", data: names.map((n) => s[n].cv_macro_f1_mean ?? null), itemStyle: { color: "#cfc2ae", borderRadius: [4, 4, 0, 0] } },
        { name: "validation", type: "bar", data: names.map((n) => s[n].validation.macro_f1), itemStyle: { color: C.violet, borderRadius: [4, 4, 0, 0] } },
        { name: "sealed test", type: "bar", data: names.map((n) => t.families[n].macro_f1), itemStyle: { color: C.btc, borderRadius: [4, 4, 0, 0], shadowBlur: 12, shadowColor: C.btc } },
      ],
    };
    const curveOpt = (kind: "roc" | "pr") => ({
      tooltip: tooltip({ trigger: "item" }), legend: legend({ bottom: 0 }),
      grid: { left: 44, right: 12, top: 12, bottom: 58 },
      xAxis: { type: "value", min: 0, max: 1, name: kind === "roc" ? "false positive rate" : "recall", nameLocation: "middle", nameGap: 24, ...axis() },
      yAxis: { type: "value", min: 0, max: 1, name: kind === "roc" ? "true positive rate" : "precision", ...axis() },
      series: [
        ...["tree", "knn", "svm_linear", "svm_rbf"].map((k, i) => ({
          name: `${FAM[k]} (${kind === "roc" ? "AUC " + fmt(t.families[k].solo_roc_auc, 2) : "AP " + fmt(t.families[k].solo_average_precision, 2)})`,
          type: "line", showSymbol: false, data: t.curves[k][kind], lineStyle: glowLine(PALETTE[[1, 2, 4, 0][i]], 2) })),
        kind === "roc"
          ? { name: "chance", type: "line", showSymbol: false, data: [[0, 0], [1, 1]], lineStyle: { type: "dotted", color: C.muted } }
          : { name: "base rate", type: "line", showSymbol: false, data: [[0, t.families.tree.solo_base_rate], [1, t.families.tree.solo_base_rate]], lineStyle: { type: "dotted", color: C.muted } },
      ],
    });
    const mon = t.monthly as Dict[];
    const driftOpt = {
      tooltip: tooltip({ valueFormatter: (v: number) => fmt(v, 3) }), legend: legend({ top: 0 }),
      grid: { left: 44, right: 12, top: 30, bottom: 30 },
      xAxis: { type: "category", data: mon.map((r) => r.month), ...axis() },
      yAxis: { type: "value", ...axis() },
      series: [
        { name: "macro-F1", type: "line", data: mon.map((r) => r.macro_f1), lineStyle: glowLine(C.cyan), symbolSize: 6, itemStyle: { color: C.cyan } },
        { name: "balanced accuracy", type: "line", data: mon.map((r) => r.balanced_accuracy), lineStyle: glowLine(C.magenta), symbolSize: 6, itemStyle: { color: C.magenta } },
      ],
    };
    const imp = (data.models.importance as Dict[]).slice(0, 14).reverse();
    const impOpt = {
      tooltip: tooltip({ trigger: "item", valueFormatter: (v: number) => fmt(v, 4) }),
      grid: { left: 150, right: 20, top: 6, bottom: 20 },
      xAxis: { type: "value", ...axis() },
      yAxis: { type: "category", data: imp.map((r) => r.feature), ...axis({ axisLabel: { color: C.text2, fontSize: 11, fontFamily: "JetBrains Mono Variable" } }) },
      series: [{ type: "bar", data: imp.map((r) => r.mean), itemStyle: { color: { type: "linear", x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: C.violet }, { offset: 1, color: C.cyan }] }, borderRadius: 4, shadowBlur: 10, shadowColor: C.cyan } }],
    };
    return { confOpt, cmpOpt, roc: curveOpt("roc"), pr: curveOpt("pr"), driftOpt, impOpt, labels, M };
  }, [data, norm]);

  if (error) return <Err msg={error} />;
  if (!data || !charts) return <Loading />;
  const t = data.models.test, sel = data.models.selection, nb = data.radar.new_blocks, nested = data.models.nested_cv;
  const op = t.families[t.operational_family];
  const pc = t.per_class as Record<string, Dict>;
  const cellBlocks = cell ? (data.radar.test_tail as Dict[]).filter((b) => b.true === cell[0] && b.pred === cell[1]).slice(-6) : [];
  return (
    <>
      <PageHead kicker="Q1 · Classification" title="Block" accent="Radar">
        Every block carries side-channel fingerprints of the software that built it: how the 32-bit version field is rolled, which nonce
        bits come up, how far the timestamp runs ahead, and how the miner fills the block relative to that day's mempool. Coinbase text and
        payout addresses — where the label comes from — are <b>excluded</b>, so the model must recognise miners from behaviour alone.
      </PageHead>
      <div className="grid g5">
        <Kpi label="Operational model" value={FAM[t.operational_family]} note={`frozen ${sel.frozen_at.slice(0, 10)} · ${sel.features.length} features`} glow="violet" />
        <Kpi label="Test macro-F1" value={fmt(op.macro_f1, 3)} note={`95% CI ${fmt(t.bootstrap.macro_f1_95ci[0], 3)}–${fmt(t.bootstrap.macro_f1_95ci[1], 3)} (day bootstrap)`} glow="cyan" />
        <Kpi label="Top-3 / family accuracy" value={`${pct(op.top3_accuracy, 0)} · ${pct(op.family_accuracy, 0)}`} note={`true pool in top 3 · accuracy once template families are merged (pool-level ${pct(op.accuracy, 0)})`} glow="btc" />
        <Kpi label="Nested CV (tree)" value={`${fmt(nested.mean, 3)} ± ${fmt(nested.sd, 3)}`} note="outer 5 × inner 3, month-grouped" glow="lime" />
        <Kpi label="Unseen Nov-2026 blocks" value={pct(nb.accuracy, 1)} note={`${int(nb.labelled)} blocks mined after the freeze`} glow="magenta" />
      </div>

      <div className="grid g-side mt">
        <Panel title="Who looks like whom?" sub="Test-period confusion matrix (2025-04 → 2026-10). Off-diagonal mass = pools whose blocks are built the same way. Click a cell to see example blocks."
          tag={<Seg label="normalisation" value={norm} onChange={setNorm} options={[{ v: "recall", label: "row %" }, { v: "count", label: "counts" }]} />}>
          <EChart option={charts.confOpt} height={470} ariaLabel="Confusion matrix of the operational model on the test period"
            onClick={(p) => { const d = p.data as number[]; if (d) setCell([charts.labels[d[1]], charts.labels[d[0]]]); }} />
          {cell && (
            <div className="callout violet">
              <b>{cell[0]}</b> predicted as <b>{cell[1]}</b>: {int(charts.M[charts.labels.indexOf(cell[0])][charts.labels.indexOf(cell[1])])} test blocks.
              {cellBlocks.length > 0 && <> Recent examples: {cellBlocks.map((b) => `#${b.height}`).join(", ")}.</>}
            </div>
          )}
        </Panel>
        <Panel title="Unseen blocks after the freeze" sub={`Mined ${nb.period[0]} → ${nb.period[1]}. Predictions were made first; labels are revealed on demand.`}
          tag={<button type="button" className="btn" onClick={() => setReveal((v) => !v)}>{reveal ? "Hide labels" : "Reveal labels"}</button>}>
          <div className="feed">
            {(nb.examples as Dict[]).slice().reverse().map((e, i) => (
              <div className="block-row" key={e.height} style={{ animationDelay: `${i * 50}ms` }}>
                <span className="h">#{int(e.height)}</span>
                <span className="m">predicted <b>{e.predicted}</b><small>{e.time.slice(0, 16)} UTC</small></span>
                {reveal ? <span className={`tag ${e.correct ? "lime" : "red"}`}>{e.correct ? "✓" : "✗"} {e.revealed_label}</span> : <span className="tag muted">hidden</span>}
              </div>
            ))}
          </div>
          <p className="caption">Accuracy over all {int(nb.labelled)} labelled new blocks: <b className="num">{pct(nb.accuracy, 1)}</b>. Solo blocks in this window: {nb.solo_in_new}.</p>
        </Panel>
      </div>

      <div className="grid g3 mt">
        <Panel title="Model comparison" sub="Same features, same blocks. Grey/violet/orange = CV / out-of-time validation / sealed test.">
          <EChart option={charts.cmpOpt} height={300} ariaLabel="Macro-F1 by model family across CV, validation and test" />
        </Panel>
        <Panel title="Solo vs rest · ROC" sub="One-vs-rest ranking of the rare Solo class. SVM scores are decision values, not probabilities.">
          <EChart option={charts.roc} height={300} ariaLabel="ROC curves for the Solo class" />
        </Panel>
        <Panel title="Solo vs rest · precision–recall" sub={`Base rate ${pct(t.families.tree.solo_base_rate, 3)} — PR is the honest view for a needle-in-haystack class.`}>
          <EChart option={charts.pr} height={300} ariaLabel="Precision-recall curves for the Solo class" />
        </Panel>
      </div>

      <div className="grid g3 mt">
        <Panel title="Per-class scorecard" sub="Precision = when we say 'pool X', how often right; recall = share of X's blocks we find.">
          <div className="table-wrap" style={{ maxHeight: 330 }}>
            <table className="data">
              <thead><tr><th>class</th><th>precision</th><th>recall</th><th>F1</th><th>blocks</th></tr></thead>
              <tbody>{charts.labels.map((l) => (
                <tr key={l}><td className="txt">{l}</td><td>{fmt(pc[l].precision, 2)}</td><td>{fmt(pc[l].recall, 2)}</td>
                  <td className={pc[l]["f1-score"] > 0.6 ? "ok" : pc[l]["f1-score"] < 0.25 ? "bad" : "warn"}>{fmt(pc[l]["f1-score"], 2)}</td><td>{int(pc[l].support)}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </Panel>
        <Panel title="What carries the signal?" sub="Permutation importance on the test period: drop in macro-F1 when one feature is shuffled.">
          <EChart option={charts.impOpt} height={330} ariaLabel="Permutation importance of the top features" />
        </Panel>
        <Panel title="Newcomer pools: whose template do they use?" sub="Pools too small in 2019–23 to get a class, mapped by the frozen model. A dominant mapping hints at a shared block template.">
          <div className="table-wrap" style={{ maxHeight: 330 }}>
            <table className="data">
              <thead><tr><th>pool</th><th>blocks</th><th>looks like</th><th>share</th></tr></thead>
              <tbody>{(t.newcomer_pools as Dict[]).slice(0, 16).map((r) => (
                <tr key={r.miner}><td className="txt">{r.miner}</td><td>{int(r.blocks)}</td><td className="txt">{r.top_prediction}</td>
                  <td className={r.top_share > 0.6 ? "ok" : ""}>{pct(r.top_share, 0)}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </Panel>
      </div>

      <div className="grid g2 mt">
        <Panel title="Drift across the test period" sub="Monthly scores of the frozen model. Pools update firmware and policies; a fingerprint model ages.">
          <EChart option={charts.driftOpt} height={260} ariaLabel="Monthly macro-F1 and balanced accuracy in the test period" />
        </Panel>
        <Panel title="Solo operating point" sub="Flag a block as 'solo-like' when the tree's Solo probability passes the threshold frozen on validation.">
          <div className="grid g3">
            <Kpi label="threshold" value={fmt(t.solo_operating_point.threshold, 3)} glow="violet" />
            <Kpi label="precision" value={pct(t.solo_operating_point.precision, 0)} note={`${t.solo_operating_point.true_positives} / ${t.solo_operating_point.flagged} flagged`} glow="lime" />
            <Kpi label="recall" value={pct(t.solo_operating_point.recall, 0)} note={`of ${t.solo_operating_point.solo_in_test} solo test blocks`} glow="magenta" />
          </div>
          <div className="callout cyan">Rule frozen before testing: <b>{sel.solo_threshold.rule}</b>. With so few solo blocks per year, these numbers have wide uncertainty — they are reported, not tuned.</div>
        </Panel>
      </div>
    </>
  );
}
