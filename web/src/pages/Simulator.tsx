import { useEffect, useMemo, useState } from "react";
import { C, EChart, axis, tooltip } from "../components/EChart";
import { Bar, Err, Kpi, Loading, PageHead, Panel } from "../components/ui";
import { useData, type Dict, type TreeExport } from "../lib/data";
import { fmt, int, pct } from "../lib/format";
import { traverse } from "../lib/tree";

const DESCR: Record<string, string> = {
  ver_rolled: "version bits 13–28 rolled (ASICBoost)", ver_roll_popcount: "number of rolled version bits", ver_bip9: "BIP9 top bits = 001",
  ver_signal_bits: "soft-fork signal bits set", ts_minus_median_s: "timestamp − median of last 11 (s)", interval_prev_s: "seconds since previous block",
  log_tx_count: "log(1 + transactions)", is_empty: "coinbase-only (empty) block", fullness: "weight / 4,000,000", witness_tx_share: "share of SegWit txs",
  witness_byte_share: "witness bytes / size", io_ratio: "log outputs − log inputs", avg_tx_vbytes: "log mean tx vsize", log_fee_total: "log(1 + fees, sat)",
  log_fee_per_kwu: "log fee rate", fee_share: "fees / total reward", log_min_fee: "log lowest fee rate included", rel_min_fee: "lowest fee rate vs day median (log)", rel_median_fee: "median fee rate vs day median (log)", rel_fee_rate: "fee rate vs day median (log)",
  rel_tx_count: "tx count vs day median (log)", rel_fullness: "fullness vs day median (log)", hour_sin: "hour of day (sin)", hour_cos: "hour of day (cos)",
};
const describe = (f: string) => DESCR[f] ?? (f.startsWith("ver_b") ? `version bit ${f.slice(5)}` : f.startsWith("nonce_b") ? `nonce bit ${f.slice(7)}` : f);

export default function Simulator() {
  const { data, error } = useData<{ tree: Dict }>(["tree"]);
  const [ex, setEx] = useState(0);
  const [x, setX] = useState<Record<string, number>>({});
  useEffect(() => { if (data) setX({ ...(data.tree.examples[0].x as Record<string, number>) }); }, [data]);
  const res = useMemo(() => (data && Object.keys(x).length ? traverse(data.tree.tree as TreeExport, x) : null), [data, x]);

  if (error) return <Err msg={error} />;
  if (!data || !res) return <Loading />;
  const T = data.tree, tree = T.tree as TreeExport, examples = T.examples as Dict[];
  const used = new Set(res.path.map((s) => s.feature));
  const ranges = T.feature_ranges as Record<string, Dict>;
  const feats = (T.features as string[]).slice().sort((a, b) => Number(used.has(b)) - Number(used.has(a)));
  const dist = Object.entries(res.dist).sort((a, b) => b[1] - a[1]);
  const pick = (i: number) => { setEx(i); setX({ ...(examples[i].x as Record<string, number>) }); };
  const rs = T.root_split as Dict;
  const knn = T.knn_example as Dict | null;
  const distOpt = {
    tooltip: tooltip({ trigger: "item", valueFormatter: (v: number) => pct(v, 1) }),
    grid: { left: 110, right: 30, top: 6, bottom: 16 },
    xAxis: { type: "value", max: 1, ...axis({ axisLabel: { color: C.muted, formatter: (v: number) => pct(v, 0) } }) },
    yAxis: { type: "category", inverse: true, data: dist.slice(0, 8).map((d) => d[0]), ...axis({ axisLabel: { color: C.text2 } }) },
    series: [{ type: "bar", data: dist.slice(0, 8).map((d, i) => ({ value: d[1], itemStyle: { color: i === 0 ? C.btc : C.violet, shadowBlur: i === 0 ? 14 : 0, shadowColor: C.btc, borderRadius: 4 } })),
      label: { show: true, position: "right", color: C.text, formatter: (p: Dict) => pct(p.value, 0) } }],
  };
  return (
    <>
      <PageHead kicker="Q1 · Explain the decision tree" title="Fingerprint" accent="Lab">
        Load a real block from the sealed test period, then change its fingerprint and watch the fitted tree re-route it — this is the
        exact {tree.criterion} tree the pipeline trained (depth {tree.depth}, {int(tree.leaves)} leaves), evaluated in your browser.
      </PageHead>
      <div className="grid g-side-l">
        <Panel title="1 · Pick a real block" sub="All solo blocks of the test period plus a sample of each pool.">
          <div className="field" style={{ marginBottom: 12 }}>
            <label htmlFor="ex">test-period block</label>
            <select id="ex" value={ex} onChange={(e) => pick(Number(e.target.value))}>
              {examples.map((e, i) => <option key={e.height} value={i}>#{e.height} · {e.miner} ({e.class})</option>)}
            </select>
          </div>
          <div className="callout"><b>True label:</b> {examples[ex].miner} → class <b>{examples[ex].class}</b><br />mined {examples[ex].time} UTC</div>
          <h3 style={{ marginTop: 16 }}>2 · Edit the fingerprint</h3>
          <p className="sub">Features on the current path are listed first (★). Binary features are toggles.</p>
          <div style={{ maxHeight: 520, overflow: "auto", paddingRight: 6 }}>
            {feats.map((f) => {
              const r = ranges[f];
              const v = x[f] ?? 0;
              return (
                <div className="field" key={f} style={{ marginBottom: 10 }}>
                  <span className="lab">{used.has(f) ? "★ " : ""}{f} <span className="val">{r.binary ? (v >= 0.5 ? "1" : "0") : fmt(v, 3)}</span></span>
                  {r.binary
                    ? <button type="button" className="btn ghost" onClick={() => setX({ ...x, [f]: v >= 0.5 ? 0 : 1 })} aria-pressed={v >= 0.5}>{describe(f)}: {v >= 0.5 ? "ON" : "OFF"}</button>
                    : <><input type="range" aria-label={f} min={Math.min(r.min, v)} max={Math.max(r.max, v)} step={(Math.max(r.max, v) - Math.min(r.min, v)) / 200 || 0.01} value={v}
                        onChange={(e) => setX({ ...x, [f]: Number(e.target.value) })} /><small style={{ color: "var(--muted)" }}>{describe(f)}</small></>}
                </div>
              );
            })}
          </div>
          <button type="button" className="btn" onClick={() => pick(ex)}>Reset to real values</button>
        </Panel>

        <div className="grid">
          <div className="grid g3">
            <Kpi label="Tree verdict" value={res.predict} note={`leaf #${res.leaf} · ${int(res.samples)} training blocks`} glow={res.predict === "Solo" ? "magenta" : "btc"} />
            <Kpi label="Confidence" value={pct(dist[0][1], 0)} note="share of the leaf's (weighted) training blocks" glow="cyan" />
            <Kpi label="Matches truth?" value={res.predict === examples[ex].class ? "YES" : "NO"} note="against the hidden coinbase-tag label" glow={res.predict === examples[ex].class ? "lime" : "red"} />
          </div>
          <Panel title="3 · Root-to-leaf path" sub="Each test compares one fingerprint with a learnt threshold (≤ goes left, as in scikit-learn).">
            <div className="path">
              {res.path.map((s, i) => (
                <div className="step" key={s.node} style={{ animationDelay: `${i * 60}ms` }}>
                  <span className="n">{i + 1}</span>
                  <span><b className="num">{s.feature}</b> = <span className="num">{fmt(s.value, 3)}</span> {s.left ? "≤" : ">"} <span className="num">{fmt(s.threshold, 3)}</span><br /><small style={{ color: "var(--muted)" }}>{describe(s.feature)}</small></span>
                  <span className={`tag ${s.left ? "cyan" : "violet"}`}>{s.left ? "← left" : "right →"}</span>
                </div>
              ))}
              <div className="step leaf"><span className="n">✓</span><span>Leaf #{res.leaf}: predict <b>{res.predict}</b></span><span className="tag btc">{pct(dist[0][1], 0)}</span></div>
            </div>
          </Panel>
          <Panel title="Leaf class distribution">
            <EChart option={distOpt} height={220} ariaLabel="Class distribution in the reached leaf" />
          </Panel>
          <div className="grid g2">
            <Panel title="Worked split at the root" sub={`Recomputed by hand on ${int(rs.n)} training blocks (unweighted counts).`}>
              <table className="data">
                <tbody>
                  <tr><td className="txt">test</td><td>{rs.feature} ≤ {fmt(rs.threshold, 3)}</td></tr>
                  <tr><td className="txt">left / right</td><td>{int(rs.n_left)} / {int(rs.n_right)}</td></tr>
                  <tr><td className="txt">Gini parent</td><td>{fmt(rs.gini.parent, 4)}</td></tr>
                  <tr><td className="txt">Gini left / right</td><td>{fmt(rs.gini.left, 4)} / {fmt(rs.gini.right, 4)}</td></tr>
                  <tr><td className="txt">weighted children</td><td>{fmt(rs.gini.weighted_children, 4)}</td></tr>
                  <tr><td className="txt">Gini reduction</td><td className="ok">{fmt(rs.gini.reduction, 4)}</td></tr>
                  <tr><td className="txt">entropy gain</td><td className="ok">{fmt(rs.entropy.information_gain, 4)}</td></tr>
                </tbody>
              </table>
              <p className="caption">Weighted Gini = (n<sub>L</sub>·G<sub>L</sub> + n<sub>R</sub>·G<sub>R</sub>) / n. {rs.note}</p>
            </Panel>
            {knn && (
              <Panel title="How KNN sees a solo block" sub={`Block #${knn.height}: ${knn.k} nearest training blocks (${knn.metric}, ${knn.weights}).`}>
                {Object.entries(knn.votes as Record<string, number>).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([k, v]) => (
                  <div key={k} style={{ marginBottom: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}><span>{k}</span><span className="num">{v} / {knn.k}</span></div>
                    <Bar value={v / knn.k} />
                  </div>
                ))}
                <div className="callout cyan">KNN prediction: <b>{knn.prediction}</b> · nearest distance {fmt(knn.neighbours[0].distance, 3)} (standardised features)</div>
              </Panel>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
