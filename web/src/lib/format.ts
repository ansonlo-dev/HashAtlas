// Use en-US so numbers have the same separators in every browser locale.
const nf = (d: number) => new Intl.NumberFormat("en-US", {
  maximumFractionDigits: d,
  minimumFractionDigits: d,
});

export const fmt = (x: number | null | undefined, d = 2): string =>
  (x == null || !Number.isFinite(x) ? "n/a" : nf(d).format(x));
export const int = (x: number | null | undefined): string => fmt(x, 0);
export const pct = (x: number | null | undefined, d = 1): string =>
  (x == null || !Number.isFinite(x) ? "n/a" : `${nf(d).format(x * 100)}%`);
export const usd = (x: number | null | undefined, d = 2): string =>
  x == null || !Number.isFinite(x) ? "n/a" : `${x < 0 ? "-" : ""}$${nf(d).format(Math.abs(x))}`;

/** Probability as "1 in N" for small values, otherwise a percentage. */
export function odds(p: number | null | undefined): string {
  if (p == null || !Number.isFinite(p) || p <= 0) return "n/a";
  if (p >= 0.2) return pct(p, 1);
  const n = 1 / p;
  if (n < 1000) return `1 in ${Math.round(n)}`;
  if (n < 1e6) return `1 in ${nf(1).format(n / 1000)}k`;
  return `1 in ${nf(1).format(n / 1e6)}M`;
}

/** Hash rate given in EH/s, printed with an adaptive unit. */
export function hashUnit(eh: number | null | undefined): string {
  if (eh == null || !Number.isFinite(eh)) return "n/a";
  const hs = eh * 1e18;
  const units: [number, string][] = [
    [1e21, "ZH/s"],
    [1e18, "EH/s"],
    [1e15, "PH/s"],
    [1e12, "TH/s"],
    [1e9, "GH/s"],
    [1e6, "MH/s"],
    [1e3, "kH/s"],
    [1, "H/s"],
  ];
  for (const [v, u] of units)
    if (hs >= v) return `${nf(hs / v >= 100 ? 0 : 1).format(hs / v)} ${u}`;
  return `${hs.toFixed(1)} H/s`;
}

export const years = (y: number | null | undefined): string => {
  if (y == null || !Number.isFinite(y)) return "n/a";
  if (y < 1 / 12) return `${fmt(y * 365, 0)} days`;
  if (y < 1) return `${fmt(y * 12, 1)} months`;
  if (y < 1000) return `${fmt(y, y < 10 ? 1 : 0)} years`;
  return `${fmt(y / 1000, 1)}k years`;
};
