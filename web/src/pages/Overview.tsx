import { useMemo } from "react";
import { C, EChart, ERA_COLORS, PALETTE, areaGrad, axis, glowLine, legend, tooltip } from "../components/EChart";
import { Err, Kpi, Loading, Panel } from "../components/ui";
import { useData, type Dict, type WeekRow } from "../lib/data";
import { fmt, hashUnit, int, odds, pct, usd } from "../lib/format";

const HALVINGS = ["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-20"];
const ERA_STARTS = [["CPU", "2009-01-03"], ["GPU", "2010-07-18"], ["FPGA/early ASIC", "2011-06-01"], ["ASIC", "2013-01-31"], ["Industrial ASIC", "2016-06-01"]];

function Orbit() {
  return (
    <svg className="hero-orbit" viewBox="0 0 360 360" aria-hidden="true">
      <defs>
        <radialGradient id="core"><stop offset="0" stopColor="#f7931a" stopOpacity=".9" /><stop offset="1" stopColor="#f7931a" stopOpacity="0" /></radialGradient>
      </defs>
      <circle cx="180" cy="180" r="60" fill="url(#core)" />
      {[90, 125, 160].map((r, i) => (
        <g key={r} style={{ transformOrigin: "180px 180px", animation: `spin ${18 + i * 10}s linear infinite ${i % 2 ? "reverse" : ""}` }}>
          <circle cx="180" cy="180" r={r} fill="none" stroke={["#a78bfa", "#22d3ee", "#f472b6"][i]} strokeOpacity=".35" strokeDasharray="4 7" />
          <circle cx={180 + r} cy="180" r="5" fill={["#a78bfa", "#22d3ee", "#f472b6"][i]} style={{ filter: "drop-shadow(0 0 6px currentColor)" }} />
        </g>
      ))}
      <text x="180" y="188" textAnchor="middle" fontSize="30" fontFamily="Orbitron" fill="#fff" opacity=".9">₿</text>
    </svg>
  );
}

export default function Overview() {
  const { data, error } = useData<{ meta: Dict; timeline: WeekRow[]; whomines: Dict; radar: Dict }>(["meta", "timeline", "whomines", "radar"]);
  const charts = useMemo(() => {
    if (!data) return null;
    const tl = data.timeline.filter((r) => r.h);
    const hashOpt = {
      tooltip: tooltip({ valueFormatter: (v: number) => hashUnit(v) }),
      legend: legend({ top: 0, right: 0 }),
      grid: { left: 60, right: 60, top: 34, bottom: 56 },
      xAxis: { type: "time", ...axis() },
      yAxis: [
        { type: "log", name: "hash rate (EH/s)", ...axis({ axisLabel: { color: C.muted, formatter: (v: number) => hashUnit(v) } }) },
        { type: "log", name: "J / TH", ...axis({ splitLine: { show: false } }) },
      ],
      dataZoom: [{ type: "inside" }, { type: "slider", height: 18, bottom: 8, borderColor: "transparent", backgroundColor: "rgba(255,255,255,0.03)",
        fillerColor: "rgba(167,139,250,0.18)", handleStyle: { color: C.btc }, textStyle: { color: C.muted } }],
      series: [
        { name: "network hash rate", type: "line", showSymbol: false, data: tl.map((r) => [r.w, r.h]), lineStyle: glowLine(C.violet, 2.2), areaStyle: areaGrad(C.violet, 0.25),
          markArea: { silent: true, data: ERA_STARTS.map(([n, s], i) => [{ name: n, xAxis: s, itemStyle: { color: ERA_COLORS[n] + "14" }, label: { color: ERA_COLORS[n], fontSize: 10, position: "insideTopLeft" } }, { xAxis: ERA_STARTS[i + 1]?.[1] ?? tl[tl.length - 1].w }]) },
          markLine: { silent: true, symbol: "none", lineStyle: { color: C.btc, type: "dashed", opacity: 0.7 }, label: { formatter: "halving", color: C.btc, fontSize: 10 }, data: HALVINGS.map((x) => ({ xAxis: x })) } },
        { name: "best hardware (J/TH)", type: "line", yAxisIndex: 1, step: "end", showSymbol: false, data: tl.map((r) => [r.w, r.fr]), lineStyle: glowLine(C.btc, 1.8),
          tooltip: { valueFormatter: (v: number) => `${fmt(v, 1)} J/TH` } },
      ],
    };
    const wm = data.whomines;
    const groups = Object.keys(wm.groups);
    const cols: Record<string, string> = { Unattributed: "#475569", "Solo services": C.magenta, "Other pools": "#64748b" };
    const whoOpt = {
      tooltip: tooltip({ valueFormatter: (v: number) => pct(v, 1) }),
      legend: legend({ type: "scroll", bottom: 0 }),
      grid: { left: 48, right: 16, top: 16, bottom: 52 },
      xAxis: { type: "category", data: wm.quarters, ...axis({ axisLabel: { color: C.muted, interval: 7 } }) },
      yAxis: { type: "value", max: 1, ...axis({ axisLabel: { color: C.muted, formatter: (v: number) => pct(v, 0) } }) },
      series: groups.map((g, i) => ({ name: g, type: "line", stack: "s", showSymbol: false, smooth: 0.2, data: wm.groups[g],
        lineStyle: { width: 0 }, areaStyle: { color: cols[g] ?? PALETTE[(i - 3 + PALETTE.length) % PALETTE.length], opacity: 0.88 }, emphasis: { focus: "series" } })),
    };
    const sy = Object.entries(wm.solo_by_year as Record<string, number>);
    const soloOpt = {
      tooltip: tooltip(), grid: { left: 40, right: 50, top: 24, bottom: 30 },
      xAxis: { type: "time", ...axis() },
      yAxis: [{ type: "log", min: 1e-6, max: 1, ...axis({ axisLabel: { color: C.muted, formatter: (v: number) => odds(v) } }) },
        { type: "value", name: "solo blocks / yr", ...axis({ splitLine: { show: false } }) }],
      series: [
        { name: "P(1.2 TH/s miner wins ≥1 block in a year)", type: "line", showSymbol: false, data: tl.filter((r) => r.sp).map((r) => [r.w, r.sp]), lineStyle: glowLine(C.magenta, 2),
          areaStyle: areaGrad(C.magenta, 0.2), tooltip: { valueFormatter: (v: number) => odds(v) } },
        { name: "solo-service blocks per year", type: "bar", yAxisIndex: 1, barWidth: 10, data: sy.map(([y, n]) => [`${y}-07-01`, n]),
          itemStyle: { color: C.cyan, shadowColor: C.cyan, shadowBlur: 10, borderRadius: [4, 4, 0, 0] } },
      ],
      legend: legend({ top: 0, left: 0 }),
    };
    return { hashOpt, whoOpt, soloOpt };
  }, [data]);

  if (error) return <Err msg={error} />;
  if (!data || !charts) return <Loading />;
  const m = data.meta, h = m.headline, ua = data.radar.unknown_attribution;
  return (
    <>
      <section className="panel hero">
        <Orbit />
        <div className="kicker">CDS3004 Data Mining · Agent-assisted group project</div>
        <h2 className="hero-title">Can a <span className="grad">small Bitcoin miner</span><br />still win a block?</h2>
        <p>
          We mined <b>{int(m.counts.blocks)}</b> Bitcoin blocks (2009 → {m.last_day}) to see how block production moved from
          bedroom CPUs to industrial ASIC farms, whether a block's on-chain <b>fingerprint</b> reveals who mined it — solo miner
          or pool — and what a miner in Hong Kong or elsewhere in Asia should actually do today and after the 2028 halving.
        </p>
        <div className="qa">
          <div><b>Q1 · CLASSIFY</b><span>Which entity built this block? Decision tree vs KNN vs SVM on header & body fingerprints.</span></div>
          <div><b>Q2 · CLUSTER + RULES</b><span>Do the data rediscover the CPU→GPU→ASIC eras, and which pools build blocks the same way?</span></div>
          <div><b>Q3 · DECIDE</b><span>Pool, solo lottery or switch off — by device, country electricity price and 2028 scenario.</span></div>
        </div>
      </section>

      <div className="grid g5 mt">
        <Kpi label="Network hash rate" value={hashUnit(h.hashrate_eh)} note={`vs ${hashUnit(data.timeline.find((r) => r.h)?.h)} in ${data.timeline.find((r) => r.h)?.w.slice(0, 7)}`} glow="violet" />
        <Kpi label="Home-miner odds / year" value={odds(h.solo_p_bitaxe)} note="1.2 TH/s device winning ≥ 1 block" glow="magenta" />
        <Kpi label="Fingerprint model" value={fmt(h.macro_f1_test, 3)} note={`macro-F1 on sealed 2025-26 test (95% CI ${fmt(h.macro_f1_ci[0], 2)}–${fmt(h.macro_f1_ci[1], 2)})`} glow="cyan" />
        <Kpi label="Nakamoto coefficient" value={`${h.nakamoto} → ${h.nakamoto_family}`} note="entities for >50% of blocks: by pool name → after merging fingerprint families" glow="btc" />
        <Kpi label="S21 break-even power" value={`${usd(h.breakeven_s21, 3)}/kWh`} note={`at ${usd(h.price_usd, 0)} BTC · hash price ${usd(h.hashprice, 4)}/TH/day`} glow="lime" />
      </div>

      <div className="grid g-side mt">
        <Panel title="Seventeen years of hash power" sub="Weekly network hash rate (log scale) with hardware eras, halvings and the energy efficiency of the best hardware available.">
          <EChart option={charts.hashOpt} height={360} ariaLabel="Network hash rate since 2009 on a log scale with hardware eras and halvings" />
        </Panel>
        <Panel title="Live-from-history block feed" sub={`The last blocks before the freeze, as the frozen model saw them. ${pct(ua.unknown_share, 1)} of the last year's blocks carry no pool tag.`}>
          <div className="feed">
            {(data.radar.test_tail as Dict[]).slice(-14).reverse().map((b, i) => (
              <div className="block-row" key={b.height} style={{ animationDelay: `${i * 40}ms` }}>
                <span className="h">#{int(b.height)}</span>
                <span className="m">{b.miner}<small>{b.time.slice(0, 16)} · {b.tx} tx · {pct(b.full, 0)} full</small></span>
                <span className={`tag ${b.pred === b.true ? "lime" : "red"}`} title="model prediction">{b.pred === b.true ? "✓" : "✗"} {b.pred}</span>
              </div>
            ))}
          </div>
          <p className="caption">✓ = fingerprint prediction matches the coinbase-tag label (hidden from the model).</p>
        </Panel>
      </div>

      <div className="grid g2 mt">
        <Panel title="Who wins blocks?" sub="Quarterly share of blocks by miner. Unattributed early blocks were mostly individual CPU/GPU miners; pools took over by 2013–14.">
          <EChart option={charts.whoOpt} height={330} ariaLabel="Stacked area of block share by miner group per quarter" />
        </Panel>
        <Panel title="The solo lottery" sub="Chance that a 1.2 TH/s home miner finds at least one block in a year at that week's network hash rate, and blocks actually won through solo-mining services.">
          <EChart option={charts.soloOpt} height={330} ariaLabel="Solo mining odds over time and solo blocks per year" />
        </Panel>
      </div>
    </>
  );
}
