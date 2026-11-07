export interface Reduction {
  relative_reduction_pct: number;
  interval_95_pct: [number, number];
}
export interface EvaluationGroup {
  mean_wape_pct: Record<string, number>;
  median_wape_pct: Record<string, number>;
  mean_bias_pct: Record<string, number>;
  selected_relative_reduction: Record<string, Reduction>;
}
export interface FrontierPoint {
  buffer_weeks: number;
  fill_rate_pct: number;
  average_stock_weeks: number;
  logistics_seed_range_95_fill_pct: [number, number];
}
export interface FinalEvidenceReport {
  forecast: {
    groups: Record<string, EvaluationGroup>;
    configuration: {
      replicates: number;
      block_origins: number;
      seed: number;
      test_origins: number;
    };
    comparisons: {
      category: string;
      lead_weeks: number;
      selected_wape_pct: number;
      naive_wape_pct: number;
      selected_bias_pct: number;
      selected_coverage_pct: number;
      relative_reduction_pct: number;
    }[];
  };
  inventory: {
    configuration: { seeds: number };
    frontiers: Record<string, FrontierPoint[]>;
    calibration_selected_summary: Record<
      string,
      Record<
        string,
        {
          categories_qualified_on_calibration: number;
          categories_total: number;
          test_fill_pct: number | null;
          test_average_stock_weeks: number | null;
          categories_meeting_target_on_test: number;
        }
      >
    >;
    limitations: string[];
  };
}
export interface ReleaseInfo {
  version: string;
  tag: string;
  repository: string;
  commit: string;
  source_url?: string;
  release_url?: string;
}
