import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import { Details } from "../WorkflowProgress";
import { Loading, SectionTitle } from "../ui";
import { number } from "../utils";
import type { FinalEvidenceReport } from "../../../shared/evidence";

const methods: Record<string, string> = {
  naive: "Repeat last week",
  recent4: "Four-week mean",
  selected: "Validation-selected",
  ml: "Gradient boosting everywhere",
};
const colours: Record<string, string> = {
  naive: "#778680",
  recent4: "#C18B4F",
  selected: "#245A45",
  ml: "#7188B0",
};

export function FinalEvidence({
  inventoryOnly = false,
}: {
  inventoryOnly?: boolean;
}) {
  const [report, setReport] = useState<FinalEvidenceReport | null>(null);
  const [error, setError] = useState("");
  const [horizon, setHorizon] = useState("all");
  const [target, setTarget] = useState("98");
  useEffect(() => {
    let current = true;
    void api<FinalEvidenceReport>("/benchmarks/evaluation")
      .then((r) => {
        if (current) setReport(r);
      })
      .catch((e) => {
        if (current) setError(e.message);
      });
    return () => {
      current = false;
    };
  }, []);
  if (error)
    return <div className="inline-error">Evaluation unavailable: {error}</div>;
  if (!report) return <Loading label="Loading reproducible evaluation" />;
  const group = report.forecast.groups[horizon];
  const coverage = report.forecast.comparisons.map(
    (r) => r.selected_coverage_pct,
  );
  const range = group.selected_relative_reduction.naive;
  return (
    <div className="final-evidence">
      {!inventoryOnly && (
        <section className="panel ops-main-panel">
          <SectionTitle
            eyebrow="OBSERVED PUBLIC DATA · ONE PHARMACY"
            title="Forecast evaluation, including simple alternatives"
          >
            Eight category series · 52 held-out origins per lead. Selection is
            frozen on validation; the test is reported without choosing a new
            winner.
          </SectionTitle>
          <label className="evidence-horizon">
            Report horizon{" "}
            <select
              aria-label="Benchmark report horizon"
              value={horizon}
              onChange={(e) => setHorizon(e.target.value)}
            >
              <option value="all">All 1, 2 and 4-week comparisons</option>
              <option value="1">1 week</option>
              <option value="2">2 weeks</option>
              <option value="4">4 weeks</option>
            </select>
          </label>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Method</th>
                  <th>Mean WAPE ↓</th>
                  <th>Median WAPE</th>
                  <th>Mean signed bias</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(methods).map(([key, name]) => (
                  <tr
                    key={key}
                    className={key === "selected" ? "selected-row" : ""}
                  >
                    <td>{name}</td>
                    <td>{number(group.mean_wape_pct[key], 2)}%</td>
                    <td>{number(group.median_wape_pct[key], 2)}%</td>
                    <td>{number(group.mean_bias_pct[key], 2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="evaluation-facts">
            <p>
              <strong>
                {number(range.relative_reduction_pct, 1)}% lower error than last
                week
              </strong>
              <br />
              95% paired time-block range {number(range.interval_95_pct[0], 1)}–
              {number(range.interval_95_pct[1], 1)}%. The overall result is
              below the challenge’s 20% target and uses a public reference, not
              GRD’s incumbent method.
            </p>
            <p>
              <strong>
                {number(
                  group.selected_relative_reduction.recent4
                    .relative_reduction_pct,
                  1,
                )}
                % lower error than the four-week mean
              </strong>
              <br />
              Negative bias means under-forecasting. ML everywhere scored lower
              test WAPE than the selection rule; the rule has not been retuned
              on these results.
            </p>
          </div>
          <Details title="Coverage, selection and reproducibility">
            <p>
              Selected coverage ranges from {number(Math.min(...coverage), 1)}%
              to {number(Math.max(...coverage), 1)}% against 90% nominal.
              Intervals need recalibration for company use. They are displayed
              evidence; the current planner does not calculate shortage
              probabilities from them.
            </p>
            <p>
              The selected method has higher WAPE than last week in five
              comparisons, by 0.6–5.6%; the largest improvement is 34.4%. These
              are descriptive comparisons, not tests of statistical equivalence.
            </p>
            <p>
              SBA-style Croston uses α=0.1 and a 0.95 correction. On dense
              series it behaves like corrected exponential smoothing and can
              under-forecast; N05C has genuine zero-demand weeks.
            </p>
            <p>
              Bootstrap: {number(report.forecast.configuration.replicates)}{" "}
              replicates, {report.forecast.configuration.block_origins}-origin
              blocks, seed {report.forecast.configuration.seed}. Time is
              resampled in one pharmacy; categories/sites are not sampled.
              Source, prediction paths and reproduction commands accompany the
              final release.
            </p>
          </Details>
        </section>
      )}
      <section className="panel ops-main-panel">
        <SectionTitle
          eyebrow="FORECAST-DRIVEN INVENTORY · CONDITIONAL REPLAY"
          title="Service and stock across seven buffer policies"
        >
          Chronological observed sales as a demand proxy;{" "}
          {report.inventory.configuration.seeds} paired logistics seeds. Orders
          use dated forecasts and past capacity—not the future true demand mean.
        </SectionTitle>
        <div
          className="frontier-chart"
          role="img"
          aria-label="Held-out service versus normalised inventory for four forecasting methods"
        >
          <ResponsiveContainer width="100%" height={310}>
            <LineChart margin={{ top: 15, right: 30, bottom: 25, left: 12 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis
                type="number"
                dataKey="average_stock_weeks"
                domain={["auto", "auto"]}
                label={{
                  value: "Average stock / past weekly demand",
                  position: "insideBottom",
                  offset: -15,
                }}
              />
              <YAxis
                type="number"
                dataKey="fill_rate_pct"
                domain={[85, 100]}
                unit="%"
                width={55}
              />
              <Tooltip
                formatter={(v, name) => [
                  typeof v === "number" ? v.toFixed(2) + "%" : v,
                  name,
                ]}
                labelFormatter={(v) =>
                  `Stock: ${Number(v).toFixed(2)} historical weeks`
                }
              />
              <Legend verticalAlign="top" />
              <ReferenceLine y={98} stroke="#99AAA2" strokeDasharray="4 4" />
              {Object.entries(methods).map(([key, label]) => (
                <Line
                  key={key}
                  data={report.inventory.frontiers[key]}
                  dataKey="fill_rate_pct"
                  name={label}
                  stroke={colours[key]}
                  strokeWidth={key === "selected" ? 3 : 2}
                  dot={{ r: 3 }}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <label className="evidence-horizon">
          Calibration service target{" "}
          <select
            aria-label="Calibration service target"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
          >
            <option value="95">95%</option>
            <option value="98">98%</option>
          </select>
        </label>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Policy uses</th>
                <th>Categories qualified on calibration</th>
                <th>Test fill</th>
                <th>Test stock (historical weeks)</th>
                <th>Categories reaching target on test</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(methods).map(([key, name]) => {
                const r =
                  report.inventory.calibration_selected_summary[target][key];
                return (
                  <tr key={key}>
                    <td>{name}</td>
                    <td>
                      {r.categories_qualified_on_calibration}/
                      {r.categories_total}
                    </td>
                    <td>{number(r.test_fill_pct, 2)}%</td>
                    <td>{number(r.test_average_stock_weeks, 2)}</td>
                    <td>
                      {r.categories_meeting_target_on_test}/
                      {r.categories_qualified_on_calibration}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="ops-note">
          Each buffer is chosen on calibration, then frozen for test. The target
          can be missed. Rows with different qualifying categories are not
          matched-cohort comparisons. Stock is normalised before aggregation; no
          currency savings or GRD outcome is claimed.
        </p>
        <Details title="All frontier points and supply assumptions">
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Method</th>
                  <th>Buffer (weeks)</th>
                  <th>Average stock (historical weeks)</th>
                  <th>Test fill</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(methods).flatMap(([key, name]) =>
                  report.inventory.frontiers[key].map((p) => (
                    <tr key={`${key}-${p.buffer_weeks}`}>
                      <td>{name}</td>
                      <td>{p.buffer_weeks}</td>
                      <td>{number(p.average_stock_weeks, 3)}</td>
                      <td>{number(p.fill_rate_pct, 2)}%</td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </div>
          <p>
            Weekly review, 1–2-week delivery, bounded historical supplier
            capacity with disruptions, 13–52-week arrival shelf life and a
            four-week warm-up. These are declared supply assumptions; actual
            distributor stock, operating policies and pilot baselines are still
            required.
          </p>
          {report.inventory.limitations.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </Details>
      </section>
    </div>
  );
}
