import { describe, expect, it } from "vitest";
import {
  weeklyHistory,
  weeklyHistoryStart,
  riskLevel,
  remainingDispatch,
  type Observation,
  parseInstant,
} from "./utils";
import type { Data, NetworkRow, Plan } from "./types";

it("reads naive SQLite UTC and aware PostgreSQL India timestamps as the same instant", () => {
  expect(parseInstant("2026-11-01T08:00:00").getTime()).toBe(
    parseInstant("2026-11-01T13:30:00+05:30").getTime(),
  );
});

describe("decision evidence", () => {
  it("fetches only the history needed for the same fourteen complete chart weeks", () => {
    const rows: Observation[] = Array.from({ length: 400 }, (_, i) => ({
      date: new Date(Date.UTC(2025, 9, 1) + i * 86400000)
        .toISOString()
        .slice(0, 10),
      quantity: 10 + (i % 19),
      measure: "requested",
    }));
    expect(weeklyHistoryStart("2026-11-01")).toBe("2026-07-27");
    expect(weeklyHistoryStart("2026-11-04")).toBe("2026-07-27");
    for (const cutoff of ["2026-11-01", "2026-10-28", "2026-03-01"]) {
      const recent = rows.filter(
        (row) => row.date >= weeklyHistoryStart(cutoff) && row.date <= cutoff,
      );
      expect(recent.length).toBeLessThanOrEqual(104);
      expect(weeklyHistory(recent, cutoff)).toEqual(
        weeklyHistory(rows, cutoff),
      );
      expect(weeklyHistory(recent, cutoff)).toHaveLength(14);
    }
  });
  const week: Observation[] = Array.from({ length: 7 }, (_, i) => ({
    date: `2026-10-${String(26 + i).padStart(2, "0")}`,
    quantity: 10,
    measure: "requested",
  }));
  // Monday 26 October through Sunday 1 November.
  week[6].date = "2026-11-01";
  it("uses requested demand only and keeps complete Monday-Sunday weeks", () => {
    const supplied = week.map((x) => ({
      ...x,
      quantity: 4,
      measure: "supplied",
    }));
    expect(weeklyHistory([...week, ...supplied], "2026-11-01")).toEqual([
      { date: "2026-11-01", actual: 70 },
    ]);
    expect(weeklyHistory(week.slice(1), "2026-11-01")).toEqual([]);
    expect(weeklyHistory(week, "2026-10-31")).toEqual([]);
  });
  it("never treats a missing position as a healthy one", () => {
    expect(
      riskLevel(
        { status: "unknown", shortage_date: null } as NetworkRow,
        "2026-11-01",
      ),
    ).toBe("unknown");
    expect(
      riskLevel(
        { status: "shortage", shortage_date: "2026-11-03" } as NetworkRow,
        "2026-11-01",
      ),
    ).toBe("critical");
  });
  it("dispatches only the unshipped part, regardless of how much has been received", () => {
    const data = {
      shipments: [{ plan_id: "p", lines: [{ quantity: 40, received: 20 }] }],
    } as Data;
    expect(remainingDispatch(data, { id: "p", quantity: 60 } as Plan)).toBe(20);
  });
});
