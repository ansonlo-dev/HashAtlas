import { useEffect, useMemo, useState } from "react";
import { C, EChart, areaGrad, axis, glowLine, legend, tooltip } from "../components/EChart";
import { Err, Kpi, Loading, PageHead, Panel } from "../components/ui";
import { useData, type Dict, type WeekRow } from "../lib/data";
import { hashprice } from "../lib/econ";
import { fmt, int, odds, pct, usd } from "../lib/format";

const DEVICES = [{ name: "Bitaxe-class (1.2 TH/s, 18 W)", ths: 1.2, watts: 18 }, { name: "Antminer S21 (200 TH/s, 3.5 kW)", ths: 200, watts: 3500 },
  { name: "Antminer S21 XP Hyd (473 TH/s, 5.7 kW)", ths: 473, watts: 5676 }];

function Countdown({ target }: { target: string }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);
  const ms = Math.max(0, new Date(target + "T00:00:00Z").getTime() - now);
  const d = Math.floor(ms / 864e5), h = Math.floor((ms % 864e5) / 36e5), m = Math.floor((ms % 36e5) / 6e4), s = Math.floor((ms % 6e4) / 1e3);
  return <div className="countdown" aria-label={`${d} days until the median projected halving date`}>{[[d, "days"], [h, "hrs"], [m, "min"], [s, "sec"]].map(([v, l]) => <div key={l}><b>{String(v).padStart(2, "0")}</b><span>{l}</span></div>)}</div>;
}

export default function Future() {
  const { data, error } = useData<{ future: Dict; timeline: WeekRow[]; advisor: Dict }>(["future", "timeline", "advisor"]);
  const [pm, setPm] = useState(1);
  const [fee, setFee] = useState(0.05);
  const [dev, setDev] = useState(1);

  const charts = useMemo(() => {
    if (!data) return null;
    const F = data.future;
    const hk = (data.advisor.electricity as Dict[]).find((e) => e.country === "Hong Kong");
    const hkKwh = (hk?.business_usd_kwh ?? hk?.household_usd_kwh ?? 0) as number;
    const months: string[] = F.months;
    const hist = data.timeline.filter((r) => r.h && r.w >= "2021-01-01").map((r) => [r.w, r.h]);
    const he = F.hashrate_eh as Dict[];
    const fanOpt = {
      tooltip: tooltip({ valueFormatter: (v: number) => `${fmt(v, 0)} EH/s` }),
      legend: legend({ top: 0, data: ["observed", "10–90% of paths", "median path", `median (${F.sensitivity_method} window)`] }),
      grid: { left: 54, right: 16, top: 36, bottom: 30 },
      xAxis: { type: "time", ...axis() }, yAxis: { type: "value", name: "EH/s", ...axis() },
      series: [
        { name: "observed", type: "line", showSymbol: false, data: hist, lineStyle: glowLine(C.text, 1.4) },
        { name: "p10", type: "line", showSymbol: false, stack: "band", data: he.map((r) => [r.date, r.p10]), lineStyle: { opacity: 0 }, tooltip: { show: false } },
        { name: "10–90% of paths", type: "line", showSymbol: false, stack: "band", data: he.map((r) => [r.date, r.p90 - r.p10]), lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(47,72,88,0.14)" } },
        { name: "median path", type: "line", showSymbol: false, data: he.map((r) => [r.date, r.p50]), lineStyle: glowLine(C.violet, 2.4),
          markLine: { symbol: "none", data: [{ xAxis: F.halving.date_p50 }], lineStyle: { color: C.btc, type: "dashed", width: 2 }, label: { formatter: "2028 halving (median)", color: C.btc } } },
        { name: `median (${F.sensitivity_method} window)`, type: "line", showSymbol: false, data: he.map((r) => [r.date, r.sensitivity_p50]), lineStyle: { color: C.magenta, type: "dashed", width: 1.6 } },
      ],
    };
    const cl = F.client;
    const price = F.price_usd_last30 * pm;
    const hp = (key: string) => months.map((_, i) => hashprice(cl.subsidy_btc_per_day_p50[i], fee, price, cl.h_ths[key][i]));
    const hp50 = hp("p50"), hpLow = hp("p90"), hpHigh = hp("p10");
    const d = DEVICES[dev];
    const be = (arr: number[]) => arr.map((v) => (v * d.ths * 0.98) / ((d.watts / 1000) * 24));
    const hpOpt = {
      tooltip: tooltip({ valueFormatter: (v: number) => usd(v, 4) }), legend: legend({ top: 0 }),
      grid: { left: 64, right: 16, top: 58, bottom: 30 },
      xAxis: { type: "category", data: months, ...axis({ axisLabel: { color: C.muted, formatter: (v: string) => v.slice(0, 7) } }) },
      yAxis: { type: "value", name: "USD per TH/s per day", ...axis() },
      series: [
        { name: "hash price (median hash-rate path)", type: "line", showSymbol: false, data: hp50, lineStyle: glowLine(C.btc, 2.4), areaStyle: areaGrad(C.btc, 0.25) },
        { name: "if hash rate grows fast (p90)", type: "line", showSymbol: false, data: hpLow, lineStyle: { color: C.red, type: "dashed" } },
        { name: "if hash rate grows slowly (p10)", type: "line", showSymbol: false, data: hpHigh, lineStyle: { color: C.lime, type: "dashed" } },
      ],
    };
    const beOpt = {
      tooltip: tooltip({ valueFormatter: (v: number) => `${usd(v, 3)}/kWh` }), legend: legend({ top: 0 }),
      grid: { left: 60, right: 16, top: 58, bottom: 30 },
      xAxis: { type: "category", data: months, ...axis({ axisLabel: { color: C.muted, formatter: (v: string) => v.slice(0, 7) } }) },
      yAxis: { type: "value", name: "break-even USD/kWh", ...axis() },
      series: [
        { name: `${d.name.split(" (")[0]} break-even`, type: "line", showSymbol: false, data: be(hp50), lineStyle: glowLine(C.cyan, 2.4), areaStyle: areaGrad(C.cyan, 0.2) },
        { name: `Hong Kong business tariff (${usd(hkKwh, 3)})`, type: "line", showSymbol: false, data: months.map(() => hkKwh), lineStyle: { color: C.magenta, type: "dotted", width: 2 } },
      ],
    };
    const bt = F.backtest.rows as Dict[];
    const origins = Array.from(new Set(bt.map((r) => r.origin)));
    const btOpt = {
      tooltip: tooltip({ trigger: "item" }), legend: legend({ top: 0 }),
      grid: { left: 54, right: 16, top: 36, bottom: 36 },
      xAxis: { type: "category", data: [90, 180, 360, 540], name: "horizon (days)", nameLocation: "middle", nameGap: 24, ...axis() },
      yAxis: { type: "value", name: "median error vs realised (%)", ...axis() },
      series: origins.map((o, i) => ({ name: `from ${o}`, type: "bar", data: [90, 180, 360, 540].map((h) => { const r = bt.find((x) => x.origin === o && x.horizon_days === h); return r ? Number(r.median_error_pct.toFixed(1)) : null; }),
        itemStyle: { color: [C.violet, C.cyan, C.btc, C.magenta][i % 4], borderRadius: 3 } })),
    };
    const idx = (name: string) => months.findIndex((m) => m >= name);
    const pick = [months[0], F.halving.date_p50, "2029-01-01"].map((t) => Math.max(0, idx(t) === -1 ? months.length - 1 : idx(t)));
    return { fanOpt, hpOpt, beOpt, btOpt, hp50, d, be50: be(hp50), pick, months, price };
  }, [data, pm, fee, dev]);

  if (error) return <Err msg={error} />;
  if (!data || !charts) return <Loading />;
  const F = data.future, bs = F.backtest.summary;
  const pSolo = (i: number) => 1 - Math.exp(-(charts.d.ths / F.client.h_ths.p50[i]) * 144 * 365);
  return (
    <>
      <PageHead kicker="Scenario lab · not a forecast" title="Future" accent="Lab">
        The only certainty is the protocol: at height {int(F.halving.height)} the block subsidy halves from 3.125 to 1.5625 BTC. Hash-rate growth is
        simulated from {int(F.n_paths)} block-bootstrapped paths of history; price and fees are <b>your</b> scenario, not our prediction. The backtest shows
        how wrong this method would have been in the past.
      </PageHead>
      <div className="grid g4">
        <div className="panel kpi"><div className="label">Projected 2028 halving (median)</div><div className="value glow-btc">{F.halving.date_p50}</div>
          <div className="note">80% of paths: {F.halving.date_p10} → {F.halving.date_p90}</div><Countdown target={F.halving.date_p50} /></div>
        <Kpi label="Backtest coverage" value={pct(bs.coverage_80pct_band, 0)} note={`of ${bs.cases} past cases fell inside the 80% band`} glow="cyan" />
        <Kpi label="Median-path error" value={`${fmt(bs.mae_pct.median, 0)}%`} note={`vs ${fmt(bs.mae_pct.persistence, 0)}% no-growth · ${fmt(bs.mae_pct.trend, 0)}% trend (mean |error|)`} glow="violet" />
        <Kpi label="Solo odds after halving" value={odds(pSolo(charts.pick[1]))} note={`${charts.d.name.split(" (")[0]}, median hash-rate path`} glow="magenta" />
      </div>
      <div className="grid g2 mt">
        <Panel title="Hash-rate scenarios to 2029" sub={F.growth_resampling}>
          <EChart option={charts.fanOpt} height={330} ariaLabel="Fan chart of simulated network hash rate" />
        </Panel>
        <Panel title="How wrong would we have been?" sub="Same method, launched from past dates using only data available then. Positive = projection too high.">
          <EChart option={charts.btOpt} height={330} ariaLabel="Backtest error of the projection method by horizon" />
        </Panel>
      </div>
      <Panel className="mt" title="Your scenario" sub="Hash price = (subsidy ÷ (1 − fee share)) × price ÷ network hash rate. The halving cuts the subsidy term in half overnight.">
        <div className="controls">
          <div className="field" style={{ minWidth: 240 }}><span className="lab">BTC price <span className="val">{usd(charts.price, 0)} (×{fmt(pm, 2)})</span></span>
            <input type="range" aria-label="price multiplier" min={0.25} max={4} step={0.05} value={pm} onChange={(e) => setPm(Number(e.target.value))} /></div>
          <div className="field" style={{ minWidth: 240 }}><span className="lab">fee share of reward <span className="val">{pct(fee, 0)}</span></span>
            <input type="range" aria-label="fee share" min={0.01} max={0.4} step={0.01} value={fee} onChange={(e) => setFee(Number(e.target.value))} /></div>
          <div className="field"><label htmlFor="fdev">device</label>
            <select id="fdev" value={dev} onChange={(e) => setDev(Number(e.target.value))}>{DEVICES.map((d, i) => <option key={d.name} value={i}>{d.name}</option>)}</select></div>
        </div>
        <div className="grid g2">
          <EChart option={charts.hpOpt} height={300} ariaLabel="Projected hash price under the chosen scenario" />
          <EChart option={charts.beOpt} height={300} ariaLabel="Projected break-even electricity price for the chosen device" />
        </div>
        <div className="grid g3 mt">
          {["now", "one month after halving", "Jan 2029"].map((l, k) => (
            <Kpi key={l} label={`${l} · ${charts.months[charts.pick[k]]}`} value={`${usd(charts.be50[charts.pick[k]], 3)}/kWh`}
              note={`break-even · solo odds ${odds(pSolo(charts.pick[k]))} / yr`} glow={["cyan", "btc", "violet"][k]} />
          ))}
        </div>
        <div className="callout violet"><b>Scope.</b> {F.scope_statement}</div>
      </Panel>
    </>
  );
}
