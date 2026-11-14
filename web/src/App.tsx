import { lazy, Suspense, useEffect, useState } from "react";
import { Loading } from "./components/ui";
import { useData, type Dict } from "./lib/data";
import { int } from "./lib/format";

const Overview = lazy(() => import("./pages/Overview"));
const Radar = lazy(() => import("./pages/Radar"));
const Simulator = lazy(() => import("./pages/Simulator"));
const Eras = lazy(() => import("./pages/Eras"));
const Rules = lazy(() => import("./pages/Rules"));
const Advisor = lazy(() => import("./pages/Advisor"));
const Future = lazy(() => import("./pages/Future"));
const Methods = lazy(() => import("./pages/Methods"));

export const ROUTES = [
  { id: "overview", label: "Overview", ico: "01", C: Overview },
  { id: "radar", label: "Block Radar", ico: "02", C: Radar },
  { id: "simulator", label: "Fingerprint Lab", ico: "03", C: Simulator },
  { id: "eras", label: "Eras & Families", ico: "04", C: Eras },
  { id: "rules", label: "Pattern Miner", ico: "05", C: Rules },
  { id: "advisor", label: "Miner Advisor", ico: "06", C: Advisor },
  { id: "future", label: "Future Lab", ico: "07", C: Future },
  { id: "methods", label: "Methods & Data", ico: "08", C: Methods },
] as const;

const current = () => {
  const h = window.location.hash.replace(/^#\/?/, "").split("?")[0];
  return ROUTES.some((r) => r.id === h) ? h : "overview";
};

export function Logo({ className = "brand-mark" }: { className?: string }) {
  // Atlas globe (meridian + equator) with one Bitcoin-orange block pinned on it.
  return (
    <svg className={className} viewBox="0 0 48 48" aria-hidden="true">
      <rect width="48" height="48" rx="10" fill="#1b1916" />
      <circle cx="21" cy="22" r="13" fill="none" stroke="#f6f2ea" strokeWidth="2" />
      <ellipse cx="21" cy="22" rx="5.6" ry="13" fill="none" stroke="#f6f2ea" strokeWidth="1.6" />
      <path d="M8 22h26" stroke="#f6f2ea" strokeWidth="1.6" />
      <rect x="25" y="26" width="13" height="13" rx="1.5" fill="#f7931a" stroke="#1b1916" strokeWidth="2.5" />
    </svg>
  );
}

export function App() {
  const [route, setRoute] = useState(current());
  const { data } = useData<{ meta: Dict }>(["meta"]);
  useEffect(() => {
    const on = () => { setRoute(current()); window.scrollTo({ top: 0, behavior: "smooth" }); };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  const R = ROUTES.find((r) => r.id === route)!;
  useEffect(() => { document.title = `${R.label} · HashAtlas`; }, [R]);
  const m = data?.meta;
  return (
    <>
      <div className="ticker" role="status" aria-label="Data status">
        <div className="ticker-in">
          <span className="live"><i />Data frozen {m?.freeze_day ?? "…"}</span>
          {m && <><span><b>{int(m.counts.blocks)}</b> blocks</span><span className="sep">/</span>
            <span className="ver">height ≤ <b>{int(m.counts.height_max)}</b></span><span className="sep">/</span>
            <span className="ver">{m.data_version} · {m.model_version}</span></>}
          <span className="right">CDS3004 Data Mining · Lingnan University</span>
        </div>
      </div>
      <header className="masthead">
        <div className="mast-in">
          <div className="brand-row">
            <a className="brand" href="#/overview" aria-label="HashAtlas home">
              <Logo />
              <div><h1>Hash<span>Atlas</span></h1><p>Can a small Bitcoin miner still win? · A data-mining study of every block since 2009</p></div>
            </a>
            <div className="mast-meta"><b>Team HashAtlas</b><br />Agent-assisted group project · 2026/27</div>
          </div>
        </div>
      </header>
      <nav className="nav-wrap sticky-nav" aria-label="Sections">
        <div className="mast-in" style={{ paddingTop: 0 }}>
          <div className="nav" style={{ marginTop: 0 }}>
            {ROUTES.map((r) => (
              <a key={r.id} href={`#/${r.id}`} className={r.id === route ? "active" : ""} aria-current={r.id === route ? "page" : undefined}>
                <span className="ico" aria-hidden="true">{r.ico}</span>{r.label}
              </a>
            ))}
          </div>
        </div>
      </nav>
      <div className="app">
        <main>
          <Suspense fallback={<Loading />}><R.C /></Suspense>
        </main>
        <footer className="foot">
          <span>HashAtlas · CDS3004 Data Mining group project · Lingnan University 2026/27</span>
          <span>Data: Blockchair dumps, mempool.space, blockchain.com, GlobalPetrolPrices · historical analysis, not financial advice</span>
        </footer>
      </div>
    </>
  );
}
