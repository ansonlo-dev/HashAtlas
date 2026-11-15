import type { ReactNode } from "react";

export function Panel({ title, sub, tag, children, className = "", id }: {
  title?: ReactNode;
  sub?: ReactNode;
  tag?: ReactNode;
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section className={`panel ${className}`} id={id}>
      {title && <h3>{title}{tag}</h3>}
      {sub && <p className="sub">{sub}</p>}
      {children}
    </section>
  );
}

export function Kpi({ label, value, note, glow = "btc" }: {
  label: string;
  value: ReactNode;
  note?: ReactNode;
  glow?: string;
}) {
  return (
    <div className="panel kpi">
      <div className="label">{label}</div>
      <div className={`value glow-${glow}`}>{value}</div>
      {note && <div className="note">{note}</div>}
    </div>
  );
}

export function PageHead({ kicker, title, accent, children }: {
  kicker: string;
  title: string;
  accent?: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-head">
      <div>
        <div className="kicker">{kicker}</div>
        <h2>{title} {accent && <span className="accent">{accent}</span>}</h2>
        {children && <p>{children}</p>}
      </div>
    </header>
  );
}

export function Seg<T extends string>({ value, options, onChange, label }: {
  value: T;
  options: { v: T; label: string }[];
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div className="seg" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.v}
          type="button"
          role="radio"
          aria-checked={value === o.v}
          className={value === o.v ? "on" : ""}
          onClick={() => onChange(o.v)}
        >{o.label}</button>
      ))}
    </div>
  );
}

export function Loading() {
  return <div className="loading"><div><div className="spin" />DECODING BLOCKS…</div></div>;
}

export function Err({ msg }: { msg: string }) {
  return <div className="panel err">Could not load dashboard data: {msg}. Run <code>uv run hashatlas webdata</code> and rebuild.</div>;
}

export function Bar({ value }: { value: number }) {
  return <div className="bar" aria-hidden="true"><i style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} /></div>;
}
