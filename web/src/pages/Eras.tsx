import { useMemo } from "react";
import { C, EChart, ERA_COLORS, PALETTE, axis, glowLine, legend, tooltip } from "../components/EChart";
import { Err, Kpi, Loading, PageHead, Panel } from "../components/ui";
import { useData, type Dict, type WeekRow } from "../lib/data";
import { fmt, int, pct } from "../lib/format";

// Use separate palettes for fitted clusters and reference hardware-era labels.
const CL = ["#b4432f", "#1f7a6d", "#4c78a8", "#c9a227", "#7b4b94", "#d4793a", "#8a8580", "#7a9a62"];

const FEAT_LABEL: Record<string, string> = {
  log_hashrate: "hash rate (log)", hashrate_growth_30d: "30-day growth", empty_share: "empty blocks", log_tx_per_block: "tx / block (log)",
  fullness: "fullness", fee_share: "fee share", unknown_share: "unattributed", hhi: "concentration (HHI)", log_hashprice_btc: "BTC per TH (log)",
};

export default function Eras() {
  const { data, error } = useData<{ clusters: Dict; timeline: WeekRow[] }>(["clusters", "timeline"]);
  const charts = useMemo(() => {
    if (!data) return null;
    const cl = data.clusters;
    const tl = data.timeline.filter((r) => r.km != null);
    const eras = Object.keys(ERA_COLORS);
    const rows = ["hardware era", "K-means", "Ward (hier.)", "DBSCAN"];
    const pts: Dict[] = [];
    tl.forEach((r) => {
      pts.push({ value: [r.w, 0], itemStyle: { color: ERA_COLORS[r.era] } });
      pts.push({ value: [r.w, 1], itemStyle: { color: CL[r.km! % CL.length] } });
      pts.push({ value: [r.w, 2], itemStyle: { color: CL[((r.hw2 ?? 1) - 1) % CL.length] } });
      pts.push({ value: [r.w, 3], itemStyle: { color: r.db === -1 ? "#1b1916" : CL[(r.db ?? 0) % CL.length], opacity: r.db === -1 ? 1 : 0.85 } });
    });
    const stripOpt = {
      tooltip: { ...tooltip({ trigger: "item" }), formatter: (p: Dict) => `${p.value[0]} · ${rows[p.value[1]]}` },
      grid: { left: 100, right: 16, top: 10, bottom: 30 },
      xAxis: { type: "time", ...axis() },
      yAxis: { type: "category", data: rows, inverse: true, ...axis({ axisLabel: { color: C.text2 } }) },
      series: [{ type: "scatter", symbol: "rect", symbolSize: [3, 34], data: pts, animation: false, progressive: 0 }],
    };
    const el = cl.elbow as Dict[];
    const elbowOpt = {
      tooltip: tooltip(), legend: legend({ top: 0 }), grid: { left: 54, right: 50, top: 32, bottom: 30 },
      xAxis: { type: "category", data: el.map((e) => e.k), name: "K", ...axis() },
      yAxis: [{ type: "value", name: "SSE", ...axis() }, { type: "value", name: "silhouette", ...axis({ splitLine: { show: false } }) }],
      series: [
        { name: "SSE (within-cluster)", type: "line", data: el.map((e) => e.sse), lineStyle: glowLine(C.violet), itemStyle: { color: C.violet }, symbolSize: 7 },
        { name: "silhouette", type: "line", yAxisIndex: 1, data: el.map((e) => e.silhouette), lineStyle: glowLine(C.btc), itemStyle: { color: C.btc }, symbolSize: 7,
          markPoint: { data: [{ coord: [String(cl.k_selected), el.find((e) => e.k === cl.k_selected)!.silhouette], value: `K=${cl.k_selected}` }], itemStyle: { color: C.magenta } } },
      ],
    };
    const feats: string[] = cl.features;
    const profs = cl.profiles as Dict[];
    const mins = feats.map((f) => Math.min(...profs.map((p) => p.centroid[f])));
    const maxs = feats.map((f) => Math.max(...profs.map((p) => p.centroid[f])));
    const radarOpt = {
      tooltip: tooltip({ trigger: "item" }), legend: legend({ bottom: 0 }),
      radar: { indicator: feats.map((f) => ({ name: FEAT_LABEL[f] ?? f, max: 1, min: 0 })), radius: "62%", center: ["50%", "46%"],
        axisName: { color: C.text2, fontSize: 10.5 }, splitLine: { lineStyle: { color: C.grid } }, splitArea: { show: false }, axisLine: { lineStyle: { color: C.axis } } },
      series: [{ type: "radar", data: profs.map((p, i) => ({ name: `C${p.cluster} · ${p.first_week.slice(0, 4)}–${p.last_week.slice(0, 4)}`,
        value: feats.map((f, j) => (p.centroid[f] - mins[j]) / ((maxs[j] - mins[j]) || 1)),
        lineStyle: glowLine(PALETTE[i % PALETTE.length], 2), itemStyle: { color: PALETTE[i % PALETTE.length] }, areaStyle: { opacity: 0.08 } })) }],
    };
    // Dendrogram of pool families from scipy's icoord / dcoord
    const pf = cl.pool_families;
    const dn = pf.average_dendrogram;
    const segs: Dict[] = (dn.icoord as number[][]).map((xs, i) => ({
      type: "line", data: xs.map((x2, k) => [x2, dn.dcoord[i][k]]), showSymbol: false, silent: true,
      lineStyle: { color: Math.max(...dn.dcoord[i]) <= pf.family_cut_height ? C.btc : "#a8a196", width: 1.6,
        shadowBlur: Math.max(...dn.dcoord[i]) <= pf.family_cut_height ? 8 : 0, shadowColor: C.cyan } }));
    const labels: string[] = dn.ivl;
    const dendroOpt = {
      grid: { left: 44, right: 16, top: 16, bottom: 120 },
      xAxis: { type: "value", min: 0, max: labels.length * 10, interval: 10, ...axis({ splitLine: { show: false },
        axisLabel: { color: C.text2, rotate: 55, fontSize: 10.5, formatter: (v: number) => (v % 10 === 5 ? labels[(v - 5) / 10] ?? "" : "") } }),
        axisTick: { show: false } },
      yAxis: { type: "value", name: "distance", ...axis() },
      series: [...segs, { type: "line", data: [[0, pf.family_cut_height], [labels.length * 10, pf.family_cut_height]], showSymbol: false,
        lineStyle: { color: C.magenta, type: "dashed" }, silent: true }],
    };
    // SciPy leaf positions are 5, 15, 25, ...; label each leaf with a custom interval.
    (dendroOpt.xAxis as Dict).interval = 5;
    return { stripOpt, elbowOpt, radarOpt, dendroOpt, eras };
  }, [data]);

  if (error) return <Err msg={error} />;
  if (!data || !charts) return <Loading />;
  const cl = data.clusters, pf = cl.pool_families, an = cl.anomalies, kt = cl.kmeans_trace;
  return (
    <>
      <PageHead kicker="Q2 · Clustering" title="Eras &" accent="Families">
        Without telling the algorithms anything about hardware, we clustered {int(cl.weeks)} weeks of block production by how blocks were made.
        Do the groups line up with the CPU → GPU → FPGA → ASIC history? Then we clustered pools by their fingerprints to see who builds blocks alike.
      </PageHead>
      <div className="grid g5">
        <Kpi label="K-means clusters" value={cl.k_selected} note={cl.rule} glow="violet" />
        <Kpi label="ARI vs hardware eras" value={fmt(cl.ari_vs_hardware_eras.kmeans, 2)} note="1 = identical partition, 0 = chance" glow="btc" />
        <Kpi label="Seed stability" value={fmt(cl.seed_stability_ari_mean, 2)} note="mean ARI over 10 single-init runs" glow="cyan" />
        <Kpi label="DBSCAN noise weeks" value={pct(cl.dbscan_selected.noise_share, 1)} note={`eps ${fmt(cl.dbscan_selected.eps, 2)}, MinPts ${cl.dbscan_selected.min_samples}`} glow="magenta" />
        <Kpi label="Pool families" value={(pf.families as string[][]).filter((f) => f.length > 1).length} note={`multi-pool groups among ${pf.pools.length} pools`} glow="lime" />
      </div>
      <Panel className="mt" title="Rediscovering the mining eras" sub="Each tick is one week. Row 1 is the known hardware history (reference only); rows 2–4 are what three clustering families found on the same standardised rows. White = DBSCAN noise.">
        <EChart option={charts.stripOpt} height={210} ariaLabel="Timeline comparing hardware eras with K-means, Ward and DBSCAN clusters" />
        <div className="legend-dots">{charts.eras.map((e) => <span key={e}><i style={{ background: ERA_COLORS[e] }} />{e}</span>)}
          <span style={{ marginLeft: 12 }}>clusters (rows 2–4): {CL.slice(0, 4).map((c, i) => <span key={c}><i style={{ background: c }} />C{i} </span>)}<i style={{ background: "#fff" }} />noise</span></div>
      </Panel>
      <div className="grid g3 mt">
        <Panel title="Choosing K" sub="SSE always falls as K grows; we pick the silhouette maximum for K ≥ 3.">
          <EChart option={charts.elbowOpt} height={280} ariaLabel="Elbow and silhouette by K" />
        </Panel>
        <Panel title="Cluster fingerprints" sub="Centroids rescaled 0–1 per feature (radar of standardised centroids).">
          <EChart option={charts.radarOpt} height={300} ariaLabel="Radar chart of cluster centroids" />
        </Panel>
        <Panel title="Linkage comparison" sub="Same rows, four linkages, cut at the same K.">
          <table className="data">
            <thead><tr><th>linkage</th><th>cophenetic r</th><th>ARI vs K-means</th><th>ARI vs eras</th></tr></thead>
            <tbody>{Object.entries(cl.hierarchical as Record<string, Dict>).map(([k, v]) => (
              <tr key={k}><td className="txt">{k}</td><td>{fmt(v.cophenetic_correlation, 3)}</td><td>{fmt(v.ari_vs_kmeans, 2)}</td><td>{fmt(v.ari_vs_hardware_eras, 2)}</td></tr>
            ))}</tbody>
          </table>
          <p className="caption">Single linkage chains into one giant cluster (sizes {(cl.hierarchical.single.cluster_sizes as number[]).slice(0, 3).join(", ")}…); Ward favours compact, balanced eras.</p>
          <div className="callout violet"><b>Hand-checked K-means step:</b> one assignment + update from fixed seeds: SSE {fmt(kt.sse_initial_assignment, 1)} → {fmt(kt.sse_after_update, 1)} (never increases); max |Δ| vs scikit-learn centroids = {fmt(kt.max_abs_diff_vs_sklearn_centroids, 6)}.</div>
        </Panel>
      </div>
      <div className="grid g-side mt">
        <Panel title="Pool families · average-linkage dendrogram" sub={`Profiles of ${pf.pools.length} pools with ≥ 300 blocks in ${pf.window[0]} → ${pf.window[1]}: version-rolling habits, empty-block rate, fee and size policy relative to the day, timestamp offsets. Cyan merges fall below the family cut.`}>
          <EChart option={charts.dendroOpt} height={420} ariaLabel="Dendrogram of mining pools by fingerprint profile" />
        </Panel>
        <Panel title="Families found" sub="Pools that merge below the cut build blocks almost identically.">
          <div className="feed" style={{ maxHeight: 420 }}>
            {(pf.families as string[][]).map((f, i) => (
              <div key={i} className="block-row" style={{ gridTemplateColumns: "34px 1fr" }}>
                <span className="h">F{i + 1}</span>
                <span className="m">{f.join(" · ")}<small>{f.length > 1 ? `${f.length} pools share a fingerprint` : "distinct fingerprint"}</small></span>
              </div>
            ))}
          </div>
          <div className="callout">Similar fingerprints can mean a shared operator, a shared template provider or the same pool software. The data <b>suggest</b>; they do not prove ownership.</div>
        </Panel>
      </div>
      <div className="grid g2 mt">
        <Panel title="DBSCAN parameter grid" sub="eps from quantiles of the k-distance curve; MinPts counts the point itself.">
          <div className="table-wrap" style={{ maxHeight: 300 }}>
            <table className="data">
              <thead><tr><th>MinPts</th><th>eps (q)</th><th>clusters</th><th>noise</th><th>core pts</th><th>ARI vs eras</th></tr></thead>
              <tbody>{(cl.dbscan as Dict[]).map((r, i) => (
                <tr key={i} className={r.eps === cl.dbscan_selected.eps && r.min_samples === cl.dbscan_selected.min_samples ? "ok" : ""}>
                  <td>{r.min_samples}</td><td>{fmt(r.eps, 2)} ({r.eps_quantile})</td><td>{r.clusters}</td><td>{pct(r.noise_share, 1)}</td><td>{r.core_points}</td><td>{fmt(r.ari_vs_hardware_eras, 2)}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </Panel>
        <Panel title="Anomalous modern blocks (DBSCAN noise)" sub={`${int(an.rows)} sampled test-period blocks; ${pct(an.noise_share, 1)} flagged as noise.`}>
          <table className="data">
            <thead><tr><th>property</th><th>noise blocks</th><th>all blocks</th></tr></thead>
            <tbody>
              <tr><td className="txt">empty blocks</td><td>{pct(an.noise_empty_share, 1)}</td><td>{pct(an.all_empty_share, 1)}</td></tr>
              <tr><td className="txt">solo blocks</td><td>{pct(an.noise_solo_share, 2)}</td><td>{pct(an.all_solo_share, 2)}</td></tr>
            </tbody>
          </table>
          <p className="caption">Median shift of noise vs all (standard units): {Object.entries(an.noise_profile_vs_all as Record<string, number>).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 4).map(([k, v]) => `${k} ${v > 0 ? "+" : ""}${fmt(v, 2)}`).join(" · ")}</p>
          <p className="caption">Noise is not an error: it marks genuinely unusual blocks (e.g. empty or extreme-timestamp blocks).</p>
        </Panel>
      </div>
    </>
  );
}
