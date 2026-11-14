import { useMemo, useState } from "react";
import { C, EChart, axis, tooltip } from "../components/EChart";
import { Err, Kpi, Loading, PageHead, Panel, Seg } from "../components/ui";
import { useData, type Dict } from "../lib/data";
import { advise } from "../lib/econ";
import { fmt, odds, pct, usd, years } from "../lib/format";

type Tariff = "business" | "household";

export default function Advisor() {
  const { data, error } = useData<{ advisor: Dict }>(["advisor"]);
  const [dev, setDev] = useState(2);
  const [ths, setThs] = useState<number | null>(null);
  const [watts, setWatts] = useState<number | null>(null);
  const [country, setCountry] = useState("Hong Kong");
  const [tariff, setTariff] = useState<Tariff>("business");
  const [priceMul, setPriceMul] = useState(1);
  const [custom, setCustom] = useState<number | null>(null);

  const ctx = useMemo(() => {
    if (!data) return null;
    const A = data.advisor;
    const devices = A.devices as Dict[];
    const d = devices[dev];
    const T = ths ?? d.ths, W = watts ?? d.watts;
    const net = A.network.hashrate_ths_30d as number;
    const hp = (A.network.hashprice_usd_th_day_30d as number) * priceMul;
    const elec = (A.electricity as Dict[]).filter((e) => e.available);
    const row = elec.find((e) => e.country === country) ?? elec[0];
    const kwh = custom ?? (row[`${tariff}_usd_kwh`] as number | null) ?? (row.household_usd_kwh as number);
    const a = advise(T, W, kwh, net, hp, A.pool_fee);
    const ranked = elec.map((e): Dict => ({ ...e, p: (e[`${tariff}_usd_kwh`] ?? e.household_usd_kwh) as number }))
      .filter((e) => e.p != null).sort((x, y) => x.p - y.p);
    const barOpt = {
      tooltip: tooltip({ trigger: "item", valueFormatter: (v: number) => `${usd(v, 3)}/kWh` }),
      grid: { left: 50, right: 16, top: 30, bottom: 96 },
      xAxis: { type: "category", data: ranked.map((e) => e.country), ...axis({ axisLabel: { color: C.text2, rotate: 60, fontSize: 10.5 } }) },
      yAxis: { type: "value", name: `${tariff} USD/kWh`, ...axis() },
      series: [{ type: "bar", data: ranked.map((e) => ({ value: e.p, itemStyle: {
        color: e.country === country ? C.btc : e.p <= a.breakeven ? C.lime : e.asia ? C.cyan : "#cfc2ae",
        borderRadius: [4, 4, 0, 0], shadowBlur: e.country === country ? 16 : 0, shadowColor: C.btc } })),
        markLine: { symbol: "none", data: [{ yAxis: a.breakeven }], lineStyle: { color: C.magenta, width: 2, shadowBlur: 10, shadowColor: C.magenta },
          label: { formatter: `break-even ${usd(a.breakeven, 3)}`, color: C.magenta, position: "insideEndTop" } } }],
    };
    // Monthly cash flow over a year for pool vs solo expectation
    const months = Array.from({ length: 12 }, (_, i) => i + 1);
    const lineOpt = {
      tooltip: tooltip({ valueFormatter: (v: number) => usd(v, 0) }),
      grid: { left: 60, right: 16, top: 20, bottom: 30 },
      xAxis: { type: "category", data: months.map((m) => `M${m}`), ...axis() },
      yAxis: { type: "value", name: "cumulative USD", ...axis() },
      series: [
        { name: "pool: steady income − power", type: "line", data: months.map((m) => a.profit * 30.4 * m), lineStyle: { color: C.cyan, width: 2.4, shadowBlur: 10, shadowColor: C.cyan }, itemStyle: { color: C.cyan }, symbolSize: 5 },
        { name: "solo: power only (no block found)", type: "line", data: months.map((m) => -a.electricity * 30.4 * m), lineStyle: { color: C.red, type: "dashed", width: 2 }, itemStyle: { color: C.red }, symbolSize: 5 },
      ],
      legend: { textStyle: { color: C.text2 }, bottom: -4, show: false },
    };
    return { A, devices, d, T, W, kwh, a, barOpt, lineOpt, elec, row, hp, net, ranked };
  }, [data, dev, ths, watts, country, tariff, priceMul, custom]);

  if (error) return <Err msg={error} />;
  if (!data || !ctx) return <Loading />;
  const { A, devices, T, W, kwh, a, elec, hp, ranked } = ctx;
  const viable = ranked.filter((e) => e.p <= a.breakeven);
  const asiaViable = viable.filter((e) => e.asia).map((e) => e.country);
  const grid = Array.from({ length: 400 }, (_, i) => i);
  const wins = Math.round(a.pYear * 400);
  const rec = a.recommendation === "pool" ? { t: "Join a pool", g: "lime", d: "Income beats electricity: a pool turns lumpy block rewards into a steady daily payout." }
    : a.recommendation === "lottery" ? { t: "Solo = lottery ticket", g: "magenta", d: "Not profitable on power. A tiny miner only makes sense as a lottery ticket (or as a heater) — with the odds shown." }
    : { t: "Switch off", g: "red", d: "Electricity costs more than the expected income at this price; mining here destroys value." };
  return (
    <>
      <PageHead kicker="Q3 · Decision on new examples" title="Miner" accent="Advisor">
        Pick a device and a place. Using the network state at the data freeze ({A.network.date}: {fmt(A.network.hashrate_ths_30d / 1e6, 0)} EH/s,
        hash price {usd(A.network.hashprice_usd_th_day_30d, 4)} per TH/s per day, 30-day means), the advisor compares pool income, the electricity bill
        and the odds of finding a block alone.
      </PageHead>
      <div className="grid g-side-l">
        <Panel title="Set-up">
          <div className="field" style={{ marginBottom: 10 }}><label htmlFor="dev">device</label>
            <select id="dev" value={dev} onChange={(e) => { setDev(Number(e.target.value)); setThs(null); setWatts(null); }}>
              {devices.map((d, i) => <option key={d.name} value={i}>{d.name} · {d.ths} TH/s · {d.watts} W</option>)}
            </select></div>
          <div className="grid g2" style={{ gap: 10, marginBottom: 10 }}>
            <div className="field"><label htmlFor="ths">TH/s</label><input id="ths" type="number" min={0.001} step="any" value={T} onChange={(e) => setThs(Number(e.target.value) || 0.001)} /></div>
            <div className="field"><label htmlFor="w">watts</label><input id="w" type="number" min={1} step="any" value={W} onChange={(e) => setWatts(Number(e.target.value) || 1)} /></div>
          </div>
          <div className="field" style={{ marginBottom: 10 }}><label htmlFor="ct">country / economy</label>
            <select id="ct" value={country} onChange={(e) => { setCountry(e.target.value); setCustom(null); }}>
              {elec.map((e) => <option key={e.country} value={e.country}>{e.asia ? "◆ " : ""}{e.country}</option>)}
            </select></div>
          <div className="field" style={{ marginBottom: 10 }}><span className="lab">tariff</span>
            <Seg label="tariff" value={tariff} onChange={(v) => { setTariff(v); setCustom(null); }} options={[{ v: "business", label: "business" }, { v: "household", label: "household" }]} /></div>
          <div className="field" style={{ marginBottom: 10 }}><label htmlFor="kwh">electricity USD/kWh (editable)</label>
            <input id="kwh" type="number" min={0} step={0.001} value={Number(kwh.toFixed(4))} onChange={(e) => setCustom(Number(e.target.value))} /></div>
          <div className="field"><span className="lab">BTC price vs freeze <span className="val">×{fmt(priceMul, 2)}</span></span>
            <input type="range" aria-label="BTC price multiplier" min={0.25} max={3} step={0.05} value={priceMul} onChange={(e) => setPriceMul(Number(e.target.value))} /></div>
          <p className="caption">Electricity: {A.source} (dated snapshot, retail tariffs; industrial miners usually negotiate lower rates). Pool fee {pct(A.pool_fee, 0)}.</p>
        </Panel>
        <div className="grid">
          <div className="grid g4">
            <Kpi label="Pool income / day" value={usd(a.poolIncome, 2)} note={`hash price ${usd(hp, 4)} × ${fmt(T, 1)} TH/s × (1 − fee)`} glow="cyan" />
            <Kpi label="Electricity / day" value={usd(a.electricity, 2)} note={`${fmt(W / 1000, 2)} kW × 24 h × ${usd(kwh, 3)}`} glow="red" />
            <Kpi label="Profit / day" value={usd(a.profit, 2)} note={`${usd(a.profit * 365, 0)} per year`} glow={a.profit >= 0 ? "lime" : "red"} />
            <Kpi label="Break-even power price" value={`${usd(a.breakeven, 3)}`} note="per kWh, for this device" glow="btc" />
          </div>
          <Panel title={<>Verdict: <span className={`glow-${rec.g}`}>{rec.t}</span></>} sub={rec.d}>
            <div className="grid g2">
              <div>
                <div className="kicker">Solo odds for this device</div>
                <div className={`big-odds glow-magenta`}>{odds(a.pYear)}</div>
                <div style={{ color: "var(--text2)" }}>chance of ≥ 1 block in 12 months · expected wait <b>{years(a.yearsToBlock)}</b></div>
                <div className="lottery" aria-label={`${wins} of 400 cells lit`}>{grid.map((i) => <i key={i} className={i < wins ? "win" : ""} />)}</div>
                <p className="caption">Each cell = 1 in 400 miners like you. Lit cells win a block this year ({wins} lit). Block reward ≈ subsidy + fees at today's price.</p>
              </div>
              <div>
                <EChart option={ctx.lineOpt} height={250} ariaLabel="Cumulative pool profit versus solo electricity cost over 12 months" />
                <p className="caption"><span style={{ color: C.cyan }}>━</span> pool cumulative profit · <span style={{ color: C.red }}>┅</span> solo electricity spent if no block is found.</p>
              </div>
            </div>
          </Panel>
        </div>
      </div>
      <Panel className="mt" title={`Where does this device pay for its power? (${tariff} tariffs)`} sub={`Orange = selected · green = below break-even · cyan = other Asian economies · grey = rest. ${viable.length} of ${ranked.length} economies are below break-even${asiaViable.length ? `, in Asia: ${asiaViable.join(", ")}` : ", none of them in Asia"}.`}>
        <EChart option={ctx.barOpt} height={340} ariaLabel="Electricity price by country against the device break-even price" />
      </Panel>
    </>
  );
}
