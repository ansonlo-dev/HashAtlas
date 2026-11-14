import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts/core";
import { BarChart, HeatmapChart, LineChart, ScatterChart, CustomChart, RadarChart, PieChart, GraphChart } from "echarts/charts";
import {
  DataZoomComponent, GridComponent, LegendComponent, MarkAreaComponent, MarkLineComponent, MarkPointComponent,
  TooltipComponent, VisualMapComponent, RadarComponent, PolarComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsCoreOption } from "echarts/core";

echarts.use([BarChart, HeatmapChart, LineChart, ScatterChart, CustomChart, RadarChart, PieChart, GraphChart, GridComponent,
  LegendComponent, TooltipComponent, VisualMapComponent, MarkLineComponent, MarkAreaComponent, MarkPointComponent,
  DataZoomComponent, RadarComponent, PolarComponent, CanvasRenderer]);

const reduceMotion = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export const C = {
  btc: "#f7931a", cyan: "#22d3ee", violet: "#a78bfa", magenta: "#f472b6", lime: "#a3e635", blue: "#60a5fa",
  red: "#fb7185", amber: "#fbbf24", teal: "#2dd4bf", text: "#eaf0ff", text2: "#b9c2e6", muted: "#8790b8",
  grid: "rgba(140,150,255,0.10)", axis: "rgba(140,150,255,0.25)",
};
export const PALETTE = [C.btc, C.violet, C.cyan, C.magenta, C.lime, C.blue, C.amber, C.red, C.teal, "#c084fc", "#94a3b8", "#fde047"];
export const ERA_COLORS: Record<string, string> = { CPU: "#94a3b8", GPU: C.cyan, "FPGA/early ASIC": C.lime, ASIC: C.violet, "Industrial ASIC": C.btc };

/** Shared axis styling for the dark neon theme. */
export const axis = (extra: Record<string, unknown> = {}) => ({
  axisLine: { lineStyle: { color: C.axis } }, axisTick: { show: false },
  axisLabel: { color: C.muted, fontSize: 11 }, splitLine: { lineStyle: { color: C.grid } },
  nameTextStyle: { color: C.muted, fontSize: 11 }, ...extra,
});
export const tooltip = (extra: Record<string, unknown> = {}) => ({
  trigger: "axis", backgroundColor: "rgba(8,11,30,0.92)", borderColor: "rgba(167,139,250,0.5)", borderWidth: 1,
  textStyle: { color: C.text, fontSize: 12 }, extraCssText: "backdrop-filter: blur(8px); border-radius: 10px; box-shadow: 0 0 20px rgba(167,139,250,.25);",
  ...extra,
});
export const legend = (extra: Record<string, unknown> = {}) => ({ textStyle: { color: C.text2, fontSize: 11.5 }, icon: "roundRect", itemWidth: 12, itemHeight: 8, ...extra });
export const glowLine = (color: string, width = 2) => ({ width, color, shadowColor: color, shadowBlur: 12 });
export const areaGrad = (color: string, a = 0.35) => ({
  color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: color + Math.round(a * 255).toString(16).padStart(2, "0") }, { offset: 1, color: color + "00" }]),
});

export interface ChartProps {
  title?: string;
  option: EChartsCoreOption;
  height?: number;
  ariaLabel: string;
  caption?: string;
  table?: { columns: string[]; rows: (string | number | null)[][] };
  onClick?: (p: { name?: string; dataIndex?: number; seriesName?: string; data?: unknown }) => void;
}

/** ECharts wrapper: canvas renderer with glow, resize handling, accessible label, PNG export and a data table. */
export function EChart({ title, option, height = 300, ariaLabel, caption, table, onClick }: ChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const inst = useRef<echarts.ECharts | null>(null);
  const clickRef = useRef(onClick);
  clickRef.current = onClick;
  const [showTable, setShowTable] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    inst.current = chart;
    chart.on("click", (p) => clickRef.current?.(p as never));
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.dispose();
      inst.current = null;
    };
  }, []);

  useEffect(() => {
    // ECharts reads legend colours from itemStyle, even for line-only series.
    const o = option as { series?: Record<string, unknown>[] };
    if (Array.isArray(o.series)) {
      o.series = o.series.map((sr) => {
        const lc = (sr.lineStyle as { color?: unknown } | undefined)?.color;
        const ic = (sr.itemStyle as { color?: unknown } | undefined)?.color;
        return lc && !ic ? { ...sr, itemStyle: { ...(sr.itemStyle as object), color: lc } } : sr;
      });
    }
    inst.current?.setOption({ animation: !reduceMotion, animationDuration: 700, animationEasing: "cubicOut",
      backgroundColor: "transparent", textStyle: { fontFamily: "Space Grotesk Variable, sans-serif", color: C.text2 },
      color: PALETTE, ...option }, true);
  }, [option]);

  const exportPng = () => {
    const url = inst.current?.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#04050d" });
    if (!url) return;
    const a = document.createElement("a");
    a.href = url;
    a.download = `hashatlas-${(title ?? "chart").toLowerCase().replace(/[^a-z0-9]+/g, "-")}.png`;
    a.click();
  };

  return (
    <figure className="chart">
      {(title || table) && (
        <div className="chart-head">
          <figcaption>{title}</figcaption>
          <div>
            {table && <button type="button" className="link" onClick={() => setShowTable((v) => !v)} aria-expanded={showTable}>{showTable ? "hide table" : "data table"}</button>}
            <button type="button" className="link" onClick={exportPng} aria-label={`Export ${title ?? "chart"} as PNG`}>png</button>
          </div>
        </div>
      )}
      <div ref={ref} style={{ height, width: "100%" }} role="img" aria-label={ariaLabel} />
      {caption && <p className="caption">{caption}</p>}
      {table && showTable && (
        <div className="table-wrap" style={{ marginTop: 8 }}>
          <table className="data">
            <thead><tr>{table.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
            <tbody>{table.rows.slice(0, 300).map((r, i) => <tr key={i}>{r.map((v, j) => <td key={j}>{v ?? "n/a"}</td>)}</tr>)}</tbody>
          </table>
        </div>
      )}
    </figure>
  );
}
