import { expect, test } from "bun:test";
import { traverse } from "./tree";
import type { TreeExport } from "./data";

const toy: TreeExport = {
  classes: ["A", "B"], features: ["x"], depth: 1, leaves: 2, criterion: "gini",
  nodes: [
    { id: 0, leaf: false, feature: "x", threshold: 0.5, left: 1, right: 2, samples: 10, impurity: 0.5, dist: [0.5, 0.5], predict: "A" },
    { id: 1, leaf: true, feature: null, threshold: null, left: -1, right: -1, samples: 5, impurity: 0, dist: [1, 0], predict: "A" },
    { id: 2, leaf: true, feature: null, threshold: null, left: -1, right: -1, samples: 5, impurity: 0, dist: [0, 1], predict: "B" },
  ],
};

test("x <= threshold goes left, as in scikit-learn", () => {
  expect(traverse(toy, { x: 0.5 }).predict).toBe("A");
  expect(traverse(toy, { x: 0.51 }).predict).toBe("B");
  expect(traverse(toy, { x: 0 }).path.length).toBe(1);
});
