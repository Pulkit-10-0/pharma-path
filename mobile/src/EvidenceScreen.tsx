import React, { useEffect, useState } from "react";
import { router } from "expo-router";
import type { FinalEvidenceReport } from "../../shared/evidence";
import { number } from "../../shared/utils";
import { useSession } from "./session";
import { Button, Card, Disclosure, Heading, Page, Txt } from "./ui";

const names: Record<string, string> = {
  naive: "Repeat last week",
  recent4: "Four-week mean",
  selected: "Validation-selected",
  ml: "Gradient boosting everywhere",
};
export function EvidenceScreen() {
  const { api } = useSession();
  const [report, setReport] = useState<FinalEvidenceReport | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let current = true;
    if (api)
      void api
        .request<FinalEvidenceReport>("/benchmarks/evaluation")
        .then((r) => {
          if (current) setReport(r);
        })
        .catch((e) => {
          if (current) setError(e.message);
        });
    return () => {
      current = false;
    };
  }, [api]);
  const group = report?.forecast.groups.all;
  return (
    <Page
      title="Evaluation evidence"
      eyebrow="Observed public data / conditional replay"
    >
      <Button title="Back" secondary onPress={() => router.back()} />
      {error ? (
        <Card>
          <Txt>{error}</Txt>
        </Card>
      ) : !report || !group ? (
        <Card>
          <Txt>Loading reproducible evidence…</Txt>
        </Card>
      ) : (
        <>
          <Card>
            <Heading>One pharmacy. Eight category series.</Heading>
            <Txt>
              52 held-out origins per lead; 1, 2 and 4 weeks. These are public
              historical sales, separate from the generated Assam operating
              records.
            </Txt>
            <Txt small>
              Model selection is frozen on validation. This does not measure GRD
              accuracy or pilot impact.
            </Txt>
          </Card>
          {Object.entries(names).map(([key, name]) => (
            <Card key={key}>
              <Heading>{name}</Heading>
              <Txt>
                Mean WAPE {number(group.mean_wape_pct[key], 2)}% · signed bias{" "}
                {number(group.mean_bias_pct[key], 2)}%
              </Txt>
            </Card>
          ))}
          <Card>
            <Heading>Compare with stronger baselines</Heading>
            <Txt>
              {number(
                group.selected_relative_reduction.naive.relative_reduction_pct,
                1,
              )}
              % lower error than last week;{" "}
              {number(
                group.selected_relative_reduction.recent4
                  .relative_reduction_pct,
                1,
              )}
              % lower than the four-week mean.
            </Txt>
            <Txt small>
              The overall 17% result is below the official 20% target. ML
              everywhere scored lower test WAPE than the frozen selection rule.
              Negative bias signals under-forecasting.
            </Txt>
            <Txt small>
              90% nominal intervals have 61.5–98.1% held-out coverage. They are
              displayed evidence, not a shortage probability used by the
              planner.
            </Txt>
          </Card>
          <Disclosure title="Forecast-driven stock replay">
            <Card>
              <Heading>
                {report.inventory.configuration.seeds} paired logistics seeds
              </Heading>
              <Txt>
                Actual chronological sales as a demand proxy; orders use
                historical forecasts and prior supplier-capacity estimates.
                Supply conditions remain assumed.
              </Txt>
              <Txt small>
                Seven buffers. 1–2-week leads, constrained supply, 13–52-week
                arrival shelf life, four-week warm-up. No currency saving or
                owner outcome is claimed.
              </Txt>
            </Card>
            {Object.entries(names).map(([key, name]) => {
              const row =
                report.inventory.calibration_selected_summary["98"][key];
              return (
                <Card key={key}>
                  <Heading>{name}</Heading>
                  <Txt>
                    98% calibration target:{" "}
                    {row.categories_qualified_on_calibration}/
                    {row.categories_total} categories qualified.
                  </Txt>
                  <Txt>
                    Held-out fill {number(row.test_fill_pct, 2)}% · stock{" "}
                    {number(row.test_average_stock_weeks, 2)} historical weeks.
                  </Txt>
                  <Txt small>
                    {row.categories_meeting_target_on_test} categories reached
                    the target on test. Different qualifying cohorts must not be
                    treated as matched comparisons.
                  </Txt>
                </Card>
              );
            })}
          </Disclosure>
          <Disclosure title="All seven held-out buffer points">
            {report.inventory.frontiers.selected.map((point, i) => {
              const baseline = report.inventory.frontiers.naive[i];
              return (
                <Card key={point.buffer_weeks}>
                  <Heading>{point.buffer_weeks}-week buffer</Heading>
                  <Txt>
                    Selected: {number(point.fill_rate_pct, 2)}% fill ·{" "}
                    {number(point.average_stock_weeks, 2)} weeks of stock.
                  </Txt>
                  <Txt small>
                    Last week: {number(baseline.fill_rate_pct, 2)}% fill ·{" "}
                    {number(baseline.average_stock_weeks, 2)} weeks of stock.
                  </Txt>
                </Card>
              );
            })}
          </Disclosure>
          <Card>
            <Heading>Reproducible ranges</Heading>
            <Txt small>
              10,000 paired circular bootstrap replicates, eight-origin blocks,
              seed 20261107. Source, dated prediction paths, protocol and
              scripts are shipped with the final release. Ranges describe time
              sampling in one pharmacy; they do not predict GRD results.
            </Txt>
          </Card>
        </>
      )}
    </Page>
  );
}
