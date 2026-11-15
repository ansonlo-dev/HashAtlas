import { expect, test } from "bun:test";
import { advise, hashprice } from "./econ";
import { odds, hashUnit } from "./format";

test("pool income, electricity and break-even follow decide.py", () => {
  const a = advise(200, 3500, 0.1, 1e9, 0.05, 0.02);
  expect(a.poolIncome).toBeCloseTo(0.05 * 200 * 0.98, 10);
  expect(a.electricity).toBeCloseTo(3.5 * 24 * 0.1, 10);
  expect(a.breakeven).toBeCloseTo(a.poolIncome / (3.5 * 24), 10);
  expect(a.recommendation).toBe("pool");
});

test("solo probability is Poisson with 144 blocks per day", () => {
  const a = advise(1.2, 18, 0.2, 1e9, 0.05, 0.02);
  const lam = (1.2 / 1e9) * 144 * 365;
  expect(a.pYear).toBeCloseTo(1 - Math.exp(-lam), 14);
  expect(a.recommendation).toBe("lottery");
});

test("hash price scales with price and inversely with hash rate", () => {
  const h1 = hashprice(450, 0.05, 100000, 1e9);
  expect(hashprice(450, 0.05, 200000, 1e9)).toBeCloseTo(2 * h1, 10);
  expect(hashprice(450, 0.05, 100000, 2e9)).toBeCloseTo(h1 / 2, 10);
});

test("formatters", () => {
  expect(odds(0.001)).toBe("1 in 1.0k");
  expect(hashUnit(1000)).toBe("1.0 ZH/s");
});
