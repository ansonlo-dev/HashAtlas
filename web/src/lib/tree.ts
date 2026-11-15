/** Follow the exported scikit-learn tree: x <= threshold goes left. */
import type { TreeExport } from "./data";

export interface Step {
  node: number;
  feature: string;
  threshold: number;
  value: number;
  left: boolean;
}

export interface TreeResult {
  path: Step[];
  leaf: number;
  dist: Record<string, number>;
  predict: string;
  samples: number;
}

export function traverse(tree: TreeExport, x: Record<string, number>): TreeResult {
  const byId = new Map(tree.nodes.map((n) => [n.id, n]));
  let n = byId.get(0)!;
  const path: Step[] = [];
  let guard = 0;
  while (!n.leaf && guard++ < 200) {
    const v = x[n.feature!] ?? 0;
    const left = v <= n.threshold!;
    path.push({ node: n.id, feature: n.feature!, threshold: n.threshold!, value: v, left });
    const next = byId.get(left ? n.left : n.right);
    if (!next) break;
    n = next;
  }
  const dist: Record<string, number> = {};
  tree.classes.forEach((c, i) => {
    if (n.dist[i] > 0) dist[c] = n.dist[i];
  });
  return { path, leaf: n.id, dist, predict: n.predict, samples: n.samples };
}
