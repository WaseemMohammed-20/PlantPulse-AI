export interface HealthResponse {
  status: string;
  database: string;
}

export interface Overview {
  production_quantity: number;
  production_target: number;
  target_attainment_pct: number | null;
  oee_pct: number | null;
  unplanned_downtime_minutes: number;
  inspected_units: number;
  defective_units: number;
  defect_rate_pct: number | null;
}

export interface ProductionTrend {
  production_date: string;
  production_quantity: number;
  good_quantity: number;
  production_target: number;
}

export interface ProductionLine {
  line_id: number;
  line_code: string;
  line_name: string;
  factory_name: string;
  production_quantity: number;
  production_target: number;
  target_attainment_pct: number | null;
  unplanned_downtime_minutes: number;
}

export interface DowntimeCause {
  cause: string;
  is_planned: boolean;
  event_count: number;
  downtime_minutes: number;
}

export interface DowntimeMachine {
  downtime_rank: number;
  machine_id: number;
  machine_code: string;
  machine_name: string;
  production_line: string;
  factory_name: string;
  unplanned_event_count: number;
  unplanned_downtime_minutes: number;
}

export interface QualityLine {
  line_id: number;
  line_code: string;
  line_name: string;
  factory_name: string;
  inspected_units: number;
  defective_units: number;
  defect_rate_pct: number | null;
}

export interface Machine {
  machine_id: number;
  machine_code: string;
  machine_name: string;
  machine_type: string;
  rated_capacity_per_hour: number;
  line_id: number;
  line_code: string;
  line_name: string;
  factory_id: number;
  factory_name: string;
  production_quantity: number;
  production_target: number;
  target_attainment_pct: number | null;
  unplanned_downtime_minutes: number;
  inspected_units: number;
  defective_units: number;
  defect_rate_pct: number | null;
}

export interface DashboardData {
  health: HealthResponse | null;
  overview: Overview | null;
  trends: ProductionTrend[];
  lines: ProductionLine[];
  downtimeCauses: DowntimeCause[];
  downtimeMachines: DowntimeMachine[];
  qualityLines: QualityLine[];
  machines: Machine[];
  errors: Partial<Record<DashboardEndpoint, string>>;
}

export type DashboardEndpoint =
  | "health"
  | "overview"
  | "trends"
  | "lines"
  | "downtimeCauses"
  | "downtimeMachines"
  | "qualityLines"
  | "machines";

export type PageName =
  | "Overview"
  | "Production"
  | "Downtime"
  | "Quality"
  | "Machines";
