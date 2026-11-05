/** Loads the versioned static exports written by `uv run hashatlas webdata` (web/public/data/*.json). */
import { useEffect, useState } from "react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Dict = Record<string, any>;

export interface WeekRow {
  w: string; h: number | null; p: number | null; hp: number | null; be: number | null; sp: number | null;
  nk: number | null; t1: number | null; fs: number | null; es: number | null; us: number | null; fr: number | null;
  hw: string; era: string; km: number | null; hw2: number | null; db: number | null; sb: number; b: number;
}

export interface TreeNode {
  id: number; leaf: boolean; feature: string | null; threshold: number | null; left: number; right: number;
  samples: number; impurity: number; dist: number[]; predict: string;
}

export interface TreeExport { classes: string[]; features: string[]; depth: number; leaves: number; criterion: string; nodes: TreeNode[]; }

export const FILES = ["meta", "timeline", "whomines", "models", "tree", "radar", "clusters", "rules", "advisor", "future", "quality"] as const;
export type FileKey = (typeof FILES)[number];

const cache = new Map<string, Promise<unknown>>();

export function load<T = Dict>(name: FileKey): Promise<T> {
  if (!cache.has(name)) {
    cache.set(name, fetch(`./data/${name}.json`, { cache: "no-cache" }).then((r) => {
      if (!r.ok) throw new Error(`${name}.json: HTTP ${r.status}`);
      return r.json();
    }));
  }
  return cache.get(name) as Promise<T>;
}

/** React hook: loads several data files; returns null until all are ready. */
export function useData<T extends Partial<Record<FileKey, unknown>>>(names: FileKey[]): { data: T | null; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const key = names.join(",");
  useEffect(() => {
    let alive = true;
    Promise.all(names.map((n) => load(n)))
      .then((vals) => { if (alive) setData(Object.fromEntries(names.map((n, i) => [n, vals[i]])) as T); })
      .catch((e: Error) => { if (alive) setError(e.message); });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return { data, error };
}
