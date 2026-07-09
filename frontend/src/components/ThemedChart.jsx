import { useEffect, useRef } from "react";
import Chart from "chart.js/auto";

// Same font stack base.html/home_content.html set via Chart.defaults.
const CHART_FONT_FAMILY =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", ' +
  '"Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif';

/** Text/grid colors for the fixed brand palette. */
export function chartTheme() {
  return {
    textColor: "#23302e",
    gridColor: "rgba(14, 78, 76, 0.1)",
  };
}

/** Brand palette shared by the dashboard charts. */
export const CHART_COLORS = {
  primary: "#0E4E4C",
  success: "#166460",
  warning: "#C0A054",
  danger: "#9B5F45",
  info: "#D8BE7E",
  light: "#F5F2E8",
  dark: "#23302e",
};

/** Soft, muted doughnut palette from the brand colors. */
export const SOFT_PALETTE = [
  "#0E4E4C",
  "#C0A054",
  "#166460",
  "#D8BE7E",
  "#6F8D87",
  "#AA8C46",
  "#E6D7AF",
  "#8FAEAA",
];

/**
 * Chart.js canvas with the lifecycle the templates handled by hand:
 * builds the chart from `makeConfig({ textColor, gridColor })`.
 */
function ThemedChart({ makeConfig, height }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    let chart = null;
    const create = () => {
      const theme = chartTheme();
      Chart.defaults.font.family = CHART_FONT_FAMILY;
      Chart.defaults.color = theme.textColor;
      Chart.defaults.plugins.legend.labels.color = theme.textColor;
      if (chart) chart.destroy();
      chart = new Chart(canvasRef.current.getContext("2d"), makeConfig(theme));
    };
    create();
    window.addEventListener("themechange", create);
    return () => {
      window.removeEventListener("themechange", create);
      if (chart) chart.destroy();
    };
  }, [makeConfig]);

  return <canvas ref={canvasRef} style={{ height }}></canvas>;
}

export default ThemedChart;
