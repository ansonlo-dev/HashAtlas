/** Browser equivalents of decide.py; econ.test.ts checks the shared formulas. */
export interface Device {
  name: string;
  ths: number;
  watts: number;
}

export interface Advice {
  poolIncome: number;
  electricity: number;
  profit: number;
  breakeven: number;
  pYear: number;
  yearsToBlock: number;
  recommendation: "pool" | "lottery" | "none";
}

/** Pool income = hash price x TH/s x (1 - fee); electricity = kW x 24 h x price.
 * Solo: blocks arrive as a Poisson process with daily rate (ths / network TH/s) x 144. */
export function advise(
  ths: number,
  watts: number,
  priceKwh: number,
  networkThs: number,
  hashpriceUsd: number,
  poolFee: number,
): Advice {
  const poolIncome = hashpriceUsd * ths * (1 - poolFee);
  const electricity = (watts / 1000) * 24 * priceKwh;
  const lamDay = (ths / networkThs) * 144;
  const pYear = 1 - Math.exp(-lamDay * 365);
  const recommendation = poolIncome > electricity ? "pool" : ths < 50 ? "lottery" : "none";
  return {
    poolIncome,
    electricity,
    profit: poolIncome - electricity,
    breakeven: poolIncome / ((watts / 1000) * 24),
    pYear,
    yearsToBlock: lamDay > 0 ? 1 / lamDay / 365 : Infinity,
    recommendation,
  };
}

/** Hash price (USD per TH/s per day) from daily subsidy, a fee share of total reward, BTC price and network hash rate. */
export function hashprice(subsidyBtcPerDay: number, feeShare: number, priceUsd: number, networkThs: number): number {
  return (subsidyBtcPerDay / (1 - feeShare)) * priceUsd / networkThs;
}

/** Solo reward in USD when a block is found (subsidy + fees). */
export const blockRewardUsd = (subsidyBtc: number, feeShare: number, priceUsd: number) => (subsidyBtc / (1 - feeShare)) * priceUsd;
