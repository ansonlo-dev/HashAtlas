import { lazy, Suspense, useEffect, useState } from "react";
import { Background } from "./components/Background";
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
  { id: "overview", label: "Mission Control", ico: "◈", C: Overview },
  { id: "radar", label: "Block Radar", ico: "◎", C: Radar },
  { id: "simulator", label: "Fingerprint Lab", ico: "⌬", C: Simulator },
  { id: "eras", label: "Eras & Families", ico: "⟁", C: Eras },
  { id: "rules", label: "Pattern Miner", ico: "⛬", C: Rules },
  { id: "advisor", label: "Miner Advisor", ico: "⚡", C: Advisor },
  { id: "future", label: "Future Lab", ico: "⟡", C: Future },
  { id: "methods", label: "Methods & Data", ico: "☰", C: Methods },
] as const;

const current = () => {
  const h = window.location.hash.replace(/^#\/?/, "").split("?")[0];
  return ROUTES.some((r) => r.id === h) ? h : "overview";
};

function Logo() {
  return (
    <svg className="brand-mark" viewBox="0 0 48 48" aria-hidden="true">
      <defs>
        <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#f7931a" /><stop offset=".55" stopColor="#f472b6" /><stop offset="1" stopColor="#22d3ee" /></linearGradient>
      </defs>
      <path d="M24 3l18 10.5v21L24 45 6 34.5v-21z" fill="rgba(4,5,13,.6)" stroke="url(#lg)" strokeWidth="2.4" />
      <path d="M24 10l12 7v14l-12 7-12-7V17z" fill="none" stroke="url(#lg)" strokeWidth="1" opacity=".6" />
      <path d="M18 16h8a4 4 0 010 8h-8m0 0h9a4 4 0 010 8h-9V16m3-3v3m4-3v3m-4 16v3m4-3v3" fill="none" stroke="url(#lg)" strokeWidth="2.2" strokeLinecap="round" />
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
      <Background />
      <div className="app">
        <header className="topbar">
          <a className="brand" href="#/overview" aria-label="HashAtlas home">
            <Logo />
            <div><h1>HASHATLAS</h1><p>Can a small Bitcoin miner still win?</p></div>
          </a>
          {m && (
            <div className="status" aria-label="Data status">
              <span className="chip"><span className="dot" />{int(m.counts.blocks)} blocks mined</span>
              <span className="chip">height ≤ {int(m.counts.height_max)}</span>
              <span className="chip">frozen {m.freeze_day}</span>
              <span className="chip">{m.data_version} · {m.model_version}</span>
            </div>
          )}
        </header>
        <nav className="nav" aria-label="Sections">
          {ROUTES.map((r) => (
            <a key={r.id} href={`#/${r.id}`} className={r.id === route ? "active" : ""} aria-current={r.id === route ? "page" : undefined}>
              <span className="ico" aria-hidden="true">{r.ico}</span>{r.label}
            </a>
          ))}
        </nav>
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
