import { useMemo, useState } from "react";
import { C, EChart, axis, tooltip } from "../components/EChart";
import { Err, Kpi, Loading, PageHead, Panel } from "../components/ui";
import { useData, type Dict } from "../lib/data";
import { fmt, int, pct } from "../lib/format";

export default function Rules() {
  const { data, error } = useData<{ rules: Dict }>(["rules"]);
  const [minConf, setMinConf] = useState(0.5);
  const [minLift, setMinLift] = useState(1.5);
  const [cons, setCons] = useState("all");
  const [confirmedOnly, setConfirmedOnly] = useState(false);

  const view = useMemo(() => {
    if (!data) return null;
    const rs = (data.rules.rules as Dict[]).filter((r) => r.confidence >= minConf && r.lift >= minLift && (cons === "all" || r.consequent === cons) && (!confirmedOnly || r.confirmed));
    const opt = {
      tooltip: { ...tooltip({ trigger: "item" }), formatter: (p: Dict) => { const r = rs[p.dataIndex]; return `<b>${r.antecedent.join(" ∧ ")}</b><br/>→ ${r.consequent}<br/>support ${pct(r.support, 2)} · confidence ${pct(r.confidence, 1)} · lift ${fmt(r.lift, 2)}`; } },
      grid: { left: 54, right: 70, top: 14, bottom: 40 },
      xAxis: { type: "log", name: "support", nameLocation: "middle", nameGap: 26, ...axis({ axisLabel: { color: C.muted, formatter: (v: number) => pct(v, 1) } }) },
      yAxis: { type: "value", name: "confidence", min: Math.max(0, minConf - 0.05), max: 1, ...axis({ axisLabel: { color: C.muted, formatter: (v: number) => pct(v, 0) } }) },
      visualMap: { dimension: 2, min: 1, max: Math.max(2, ...rs.map((r) => r.lift)), right: 0, top: 10, itemHeight: 140, text: ["lift", ""], textStyle: { color: C.muted },
        inRange: { color: ["#3b82f6", "#a78bfa", "#f472b6", "#f7931a"] }, calculable: true },
      series: [{ type: "scatter", data: rs.map((r) => [r.support, r.confidence, r.lift, r.antecedent.length]),
        symbolSize: (v: number[]) => 8 + v[3] * 5, itemStyle: { shadowBlur: 12, shadowColor: "rgba(247,147,26,.6)", opacity: 0.9 } }],
    };
    return { rs, opt };
  }, [data, minConf, minLift, cons, confirmedOnly]);

  if (error) return <Err msg={error} />;
  if (!data || !view) return <Loading />;
  const R = data.rules, bf = R.brute_force_check, sc = R.solo_contrast;
  const consequents = Array.from(new Set((R.rules as Dict[]).map((r) => r.consequent))).sort();
  return (
    <>
      <PageHead kicker="Q2 · Association rules" title="Pattern" accent="Miner">
        Each block becomes a basket of properties (empty, full, version rolling, fees below the day's median, witness-heavy, fast follow-up…) plus
        the miner. A from-scratch Apriori finds itemsets that recur; rules <i>properties → miner</i> are kept when their lift shows real association
        and re-measured on a later window.
      </PageHead>
      <div className="grid g5">
        <Kpi label="Transactions" value={int(R.transactions)} note={`blocks ${R.discovery_window[0]} → ${R.discovery_window[1]}`} glow="violet" />
        <Kpi label="Frequent itemsets" value={int(R.frequent_itemsets)} note={`min support ${pct(R.min_support, 0)} (${int(R.min_count)} blocks)`} glow="cyan" />
        <Kpi label="Rules → miner" value={int(R.n_rules)} note={`confidence ≥ ${pct(R.min_confidence, 0)}`} glow="btc" />
        <Kpi label="Confirmed later" value={pct((R.rules as Dict[]).filter((r) => r.confirmed).length / Math.max(1, (R.rules as Dict[]).length), 0)} note={`on ${int(R.confirm_transactions)} blocks from ${R.confirm_window[0]}`} glow="lime" />
        <Kpi label="Brute-force check" value={bf.passed ? "PASSED" : "FAILED"} note={`${bf.frequent_by_brute_force} itemsets over ${bf.items_checked} items re-counted`} glow={bf.passed ? "lime" : "red"} />
      </div>
      <Panel className="mt" title="Rule explorer" sub="Drag the filters; bubble size = number of antecedent items.">
        <div className="controls">
          <div className="field" style={{ minWidth: 220 }}><span className="lab">min confidence <span className="val">{pct(minConf, 0)}</span></span>
            <input type="range" aria-label="minimum confidence" min={0.5} max={1} step={0.01} value={minConf} onChange={(e) => setMinConf(Number(e.target.value))} /></div>
          <div className="field" style={{ minWidth: 220 }}><span className="lab">min lift <span className="val">{fmt(minLift, 1)}</span></span>
            <input type="range" aria-label="minimum lift" min={1} max={10} step={0.1} value={minLift} onChange={(e) => setMinLift(Number(e.target.value))} /></div>
          <div className="field"><label htmlFor="cons">consequent</label>
            <select id="cons" value={cons} onChange={(e) => setCons(e.target.value)}>
              <option value="all">any miner</option>{consequents.map((c) => <option key={c} value={c}>{c}</option>)}
            </select></div>
          <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 13 }}><input type="checkbox" checked={confirmedOnly} onChange={(e) => setConfirmedOnly(e.target.checked)} /> confirmed on later window only</label>
          <span className="tag cyan">{view.rs.length} rules shown</span>
        </div>
        <div className="grid g2">
          <EChart option={view.opt} height={380} ariaLabel="Scatter of rules by support, confidence and lift" />
          <div className="table-wrap" style={{ maxHeight: 380 }}>
            <table className="data">
              <thead><tr><th>if block is…</th><th>then miner</th><th>supp</th><th>conf</th><th>lift</th><th>later conf</th></tr></thead>
              <tbody>{view.rs.slice(0, 80).map((r, i) => (
                <tr key={i}><td className="txt">{r.antecedent.join(" ∧ ")}</td><td className="txt">{r.consequent.replace("miner=", "")}</td>
                  <td>{pct(r.support, 1)}</td><td>{pct(r.confidence, 0)}</td><td className="ok">{fmt(r.lift, 2)}</td>
                  <td className={r.confirmed ? "ok" : "warn"}>{r.confirm_confidence == null ? "n/a" : pct(r.confirm_confidence, 0)}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </div>
        <div className="callout cyan">Confidence is a historical conditional frequency, and lift = confidence ÷ the miner's base rate. Neither proves that a property <i>causes</i> a miner — they describe how each pool's software tends to build blocks.</div>
      </Panel>
      <div className="grid g2 mt">
        <Panel title="Apriori, level by level" sub="Join frequent (k−1)-itemsets → prune candidates with an infrequent subset (anti-monotone support) → count survivors.">
          <table className="data">
            <thead><tr><th>k</th><th>joined candidates</th><th>pruned by subset</th><th>counted</th><th>frequent</th></tr></thead>
            <tbody>{(R.apriori_trace as Dict[]).map((t) => (
              <tr key={t.k}><td>{t.k}</td><td>{int(t.candidates)}</td><td className="warn">{int(t.pruned_by_subset)}</td><td>{int(t.counted)}</td><td className="ok">{int(t.frequent)}</td></tr>
            ))}</tbody>
          </table>
          <p className="caption">Verified against exhaustive enumeration of every itemset (up to size {bf.max_len}) over the first {bf.items_checked} items: {bf.missing_from_apriori} missing, {bf.wrong_counts} wrong counts.</p>
        </Panel>
        <Panel title="What makes a solo block different?" sub={`Solo blocks are too rare (${sc.solo_blocks} since 2019) for global support thresholds, so we mine frequent itemsets inside solo blocks and compare with ${int(sc.pool_blocks)} pool blocks.`}>
          <div className="table-wrap" style={{ maxHeight: 330 }}>
            <table className="data">
              <thead><tr><th>itemset</th><th>in solo</th><th>in pools</th><th>ratio</th></tr></thead>
              <tbody>{(sc.itemsets as Dict[]).slice(0, 18).map((r, i) => (
                <tr key={i}><td className="txt">{r.itemset.join(" ∧ ")}</td><td>{pct(r.support_in_solo, 0)}</td><td>{pct(r.support_in_pools, 1)}</td>
                  <td className={(r.ratio ?? 0) > 2 ? "ok" : ""}>{r.ratio == null ? "∞" : `${fmt(r.ratio, 1)}×`}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </Panel>
      </div>
    </>
  );
}
