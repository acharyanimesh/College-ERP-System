import { useEffect, useRef } from "react";
import Chart from "chart.js/auto";

// Same font stack base.html/home_content.html set via Chart.defaults.
const CHART_FONT_FAMILY =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", ' +
  '"Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif';

/**
 * Text/grid colors for the current background, exactly like the dashboard
 * templates' `isAdminBg` check: on the glass/waves backgrounds the chart
 * text and grid lines must be light to stay readable.
 */
export function chartTheme() {
  const onGlassBg =
    document.body.classList.contains("admin-bg") ||
    document.body.classList.contains("staff-bg") ||
    document.body.classList.contains("student-bg");
  return {
    textColor: onGlassBg ? "#e8f1f7" : "#262626",
    gridColor: onGlassBg ? "rgba(255, 255, 255, 0.12)" : "#f1f3f4",
  };
}

/** ERPNext-style palette shared by the dashboard charts. */
export const CHART_COLORS = {
  primary: "#5e64ff",
  success: "#28a745",
  warning: "#ffc107",
  danger: "#dc3545",
  info: "#17a2b8",
  light: "#f8f9fc",
  dark: "#262626",
};

/** Soft, muted doughnut palette from the templates. */
export const SOFT_PALETTE = [
  "#7fa8d4",
  "#8fcfb6",
  "#e6c98a",
  "#dd9a9a",
  "#86c5d9",
  "#b3a4dd",
  "#e0b48a",
  "#86c9b4",
];

/**
 * Chart.js canvas with the lifecycle the templates handled by hand:
 * builds the chart from `makeConfig({ textColor, gridColor })`, and
 * recreates it whenever the Layout dispatches `themechange` (replacing
 * base.html's window.recreateAllCharts machinery).
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
