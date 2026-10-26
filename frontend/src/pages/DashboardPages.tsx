import {
  Activity,
  AlertTriangle,
  Boxes,
  CheckCircle2,
  CircleGauge,
  Factory,
  Target,
  Timer,
  Wrench,
} from "lucide-react";
import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardData, DashboardEndpoint } from "../types";
import { KpiCard } from "../components/KpiCard";
import { Panel } from "../components/Panel";

const chartColors = {
  blue: "#3978e5",
  green: "#19a879",
  amber: "#edae42",
  red: "#e36b68",
  grid: "#edf0f4",
  text: "#8a94a4",
};

const numberFormat = new Intl.NumberFormat("en-US");
const dateFormat = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
});

function quantity(value: number | null | undefined): string {
  return value == null ? "—" : numberFormat.format(value);
}

function percent(value: number | null): string {
  return value == null ? "—" : `${value.toFixed(1)}%`;
}

function duration(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)} min`;
  const hours = Math.floor(minutes / 60);
  const remaining = Math.round(minutes % 60);
  return remaining === 0 ? `${hours}h` : `${hours}h ${remaining}m`;
}

function endpointError(data: DashboardData, key: DashboardEndpoint) {
  const error = data.errors[key];
  return error ? `Could not load this data: ${error}` : undefined;
}

function axisProps() {
  return {
    axisLine: false as const,
    tickLine: false as const,
    tick: { fill: chartColors.text, fontSize: 11 },
  };
}

function formatShortDate(value: string) {
  return dateFormat.format(new Date(`${value}T00:00:00`));
}

function TrendChart({ data }: { data: DashboardData }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data.trends} margin={{ top: 10, right: 12, left: -12, bottom: 0 }} barGap={4}>
        <CartesianGrid stroke={chartColors.grid} strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="production_date"
          tickFormatter={formatShortDate}
          interval="preserveStartEnd"
          minTickGap={24}
          {...axisProps()}
        />
        <YAxis tickFormatter={(value: number) => `${Math.round(value / 1000)}k`} {...axisProps()} />
        <Tooltip
          labelFormatter={(value) => formatShortDate(String(value))}
          formatter={(value, name) => [numberFormat.format(Number(value)), name]}
          contentStyle={{ border: "1px solid #e8ecf2", borderRadius: 10, fontSize: 12 }}
        />
        <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
        <Bar dataKey="production_quantity" name="Actual production" fill={chartColors.blue} radius={[4, 4, 0, 0]} maxBarSize={19} />
        <Bar dataKey="production_target" name="Production target" fill="#dce7fa" radius={[4, 4, 0, 0]} maxBarSize={19} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function LineChart({ data }: { data: DashboardData }) {
  const chartData = data.lines.map((line) => ({
    name: line.line_code,
    attainment: line.target_attainment_pct,
    line: line.line_name,
  }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={chartData} layout="vertical" margin={{ top: 6, right: 28, left: 4, bottom: 0 }}>
        <CartesianGrid stroke={chartColors.grid} strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" domain={[0, "dataMax + 12"]} unit="%" {...axisProps()} />
        <YAxis dataKey="name" type="category" width={82} {...axisProps()} />
        <Tooltip
          formatter={(value) => [value == null ? "—" : `${Number(value).toFixed(2)}%`, "Target attainment"]}
          labelFormatter={(label) => {
            const match = chartData.find((item) => item.name === label);
            return match ? `${match.line} · ${label}` : label;
          }}
          contentStyle={{ border: "1px solid #e8ecf2", borderRadius: 10, fontSize: 12 }}
        />
        <Bar dataKey="attainment" name="Target attainment" fill={chartColors.green} radius={[0, 5, 5, 0]} maxBarSize={20}>
          <LabelList dataKey="attainment" position="right" formatter={(value: unknown) => value == null ? "—" : `${Number(value).toFixed(0)}%`} style={{ fill: "#667286", fontSize: 10 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function CauseChart({ data }: { data: DashboardData }) {
  const chartData = data.downtimeCauses.map((item) => ({
    ...item,
    label: `${item.cause.replaceAll("_", " ")}${item.is_planned ? " · planned" : ""}`,
  }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={chartData} layout="vertical" margin={{ top: 6, right: 25, left: 8, bottom: 0 }}>
        <CartesianGrid stroke={chartColors.grid} strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" unit=" min" {...axisProps()} />
        <YAxis dataKey="label" type="category" width={126} {...axisProps()} />
        <Tooltip
          formatter={(value) => [`${Number(value).toFixed(1)} min`, "Downtime"]}
          contentStyle={{ border: "1px solid #e8ecf2", borderRadius: 10, fontSize: 12 }}
        />
        <Bar dataKey="downtime_minutes" name="Downtime" radius={[0, 5, 5, 0]} maxBarSize={20}>
          {chartData.map((item, index) => (
            <Cell key={item.cause} fill={item.is_planned ? chartColors.blue : [chartColors.amber, chartColors.red, chartColors.green, chartColors.blue][index % 4]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function MachineRanking({
  data,
  limit = 6,
}: {
  data: DashboardData;
  limit?: number;
}) {
  return (
    <div className="ranking-list">
      {data.downtimeMachines.slice(0, limit).map((machine, index) => (
        <div className="ranking-row" key={machine.machine_id}>
          <span className={`rank-number ${index < 3 ? "rank-highlight" : ""}`}>
            {String(index + 1).padStart(2, "0")}
          </span>
          <div className="rank-machine">
            <strong>{machine.machine_name}</strong>
            <span>{machine.machine_code} · {machine.production_line}</span>
          </div>
          <div className="rank-duration">
            <strong>{duration(machine.unplanned_downtime_minutes)}</strong>
            <span>{machine.unplanned_event_count} events</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function ProductionTable({ data }: { data: DashboardData }) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr><th>Production line</th><th>Facility</th><th>Actual units</th><th>Target</th><th>Attainment</th><th>Unplanned downtime</th></tr>
        </thead>
        <tbody>
          {data.lines.map((line) => (
            <tr key={line.line_id}>
              <td><strong>{line.line_name}</strong><span className="table-secondary">{line.line_code}</span></td>
              <td>{line.factory_name}</td>
              <td>{quantity(line.production_quantity)}</td>
              <td>{quantity(line.production_target)}</td>
              <td><span className={`metric-badge ${(line.target_attainment_pct ?? 0) >= 90 ? "badge-green" : "badge-amber"}`}>{percent(line.target_attainment_pct)}</span></td>
              <td>{duration(line.unplanned_downtime_minutes)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RecentProductionTable({ data }: { data: DashboardData }) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr><th>Production date</th><th>Actual units</th><th>Good units</th><th>Target</th><th>Attainment</th></tr>
        </thead>
        <tbody>
          {data.trends.slice(-7).reverse().map((record) => (
            <tr key={record.production_date}>
              <td><strong>{formatShortDate(record.production_date)}</strong></td>
              <td>{quantity(record.production_quantity)}</td>
              <td>{quantity(record.good_quantity)}</td>
              <td>{quantity(record.production_target)}</td>
              <td><span className="metric-badge badge-green">{percent(record.production_target ? (record.production_quantity / record.production_target) * 100 : null)}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function QualityTable({ data }: { data: DashboardData }) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr><th>Production line</th><th>Facility</th><th>Inspected units</th><th>Defects</th><th>Defect rate</th><th>Inspection status</th></tr>
        </thead>
        <tbody>
          {data.qualityLines.map((line) => (
            <tr key={line.line_id}>
              <td><strong>{line.line_name}</strong><span className="table-secondary">{line.line_code}</span></td>
              <td>{line.factory_name}</td>
              <td>{quantity(line.inspected_units)}</td>
              <td>{quantity(line.defective_units)}</td>
              <td><span className={`metric-badge ${(line.defect_rate_pct ?? 0) <= 3 ? "badge-green" : "badge-red"}`}>{percent(line.defect_rate_pct)}</span></td>
              <td><span className="inspection-label"><CheckCircle2 size={14} /> Recorded</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MachinesTable({ data }: { data: DashboardData }) {
  return (
    <div className="table-scroll">
      <table className="data-table machine-table">
        <thead>
          <tr><th>Machine</th><th>Production line</th><th>Factory</th><th>Production</th><th>Target attainment</th><th>30-day signal</th><th>Downtime</th><th>Defect rate</th></tr>
        </thead>
        <tbody>
          {data.machines.map((machine) => (
            <tr key={machine.machine_id}>
              <td><strong>{machine.machine_name}</strong><span className="table-secondary">{machine.machine_code} · {machine.machine_type.replaceAll("_", " ")}</span></td>
              <td>{machine.line_name}<span className="table-secondary">{machine.line_code}</span></td>
              <td>{machine.factory_name}</td>
              <td>{quantity(machine.production_quantity)}<span className="table-secondary">of {quantity(machine.production_target)}</span></td>
              <td><span className={`metric-badge ${(machine.target_attainment_pct ?? 0) >= 90 ? "badge-green" : "badge-amber"}`}>{percent(machine.target_attainment_pct)}</span></td>
              <td><span className={`metric-badge ${machine.unplanned_downtime_minutes >= 120 ? "badge-amber" : "badge-green"}`}>{machine.unplanned_downtime_minutes >= 120 ? "Review" : "Stable"}</span></td>
              <td>{duration(machine.unplanned_downtime_minutes)}</td>
              <td>{percent(machine.defect_rate_pct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function OverviewPage({ data, loading }: { data: DashboardData; loading: boolean }) {
  const overview = data.overview;
  return (
    <>
      <div className="page-intro-row">
        <div>
          <h2>Plant overview</h2>
          <p>Performance snapshot across all connected facilities.</p>
        </div>
        <span className="data-range"><span /> Last 30 days</span>
      </div>
      <div className="kpi-grid">
        <KpiCard label="Total production" value={overview ? quantity(overview.production_quantity) : "—"} detail={overview ? `Target ${quantity(overview.production_target)} units` : "Units produced"} icon={<Boxes size={19} />} tone="blue" />
        <KpiCard label="Overall equipment effectiveness" value={overview ? percent(overview.oee_pct) : "—"} detail="Availability × performance × quality" icon={<Target size={19} />} tone="green" trend={overview && (overview.oee_pct ?? 0) >= 85 ? "up" : undefined} />
        <KpiCard label="Unplanned downtime" value={overview ? duration(overview.unplanned_downtime_minutes) : "—"} detail="Across all production machines" icon={<Timer size={19} />} tone="amber" />
        <KpiCard label="Defect rate" value={overview ? percent(overview.defect_rate_pct) : "—"} detail={overview ? `${quantity(overview.defective_units)} of ${quantity(overview.inspected_units)} inspected units` : "Based on inspections"} icon={<AlertTriangle size={19} />} tone="red" />
      </div>

      <div className="dashboard-grid dashboard-grid-main">
        <Panel title="Production performance" subtitle="Daily output compared with production target" className="panel-span-two" loading={loading} error={endpointError(data, "trends")} empty={!data.trends.length} emptyMessage="No production records found.">
          <div className="chart-area chart-tall"><TrendChart data={data} /></div>
        </Panel>
        <Panel title="Line target attainment" subtitle="Production versus target by line" loading={loading} error={endpointError(data, "lines")} empty={!data.lines.length}>
          <div className="chart-area chart-tall"><LineChart data={data} /></div>
        </Panel>
      </div>

      <Panel title="Recent production records" subtitle="Daily output totals · simulated demo data" loading={loading} error={endpointError(data, "trends")} empty={!data.trends.length}>
        <RecentProductionTable data={data} />
      </Panel>

      <div className="dashboard-grid dashboard-grid-bottom">
        <Panel title="Downtime by cause" subtitle="Recorded lost time by event cause" loading={loading} error={endpointError(data, "downtimeCauses")} empty={!data.downtimeCauses.length}>
          <div className="chart-area chart-medium"><CauseChart data={data} /></div>
        </Panel>
        <Panel title="Highest downtime machines" subtitle="Ranked by unplanned lost time" action="View all" loading={loading} error={endpointError(data, "downtimeMachines")} empty={!data.downtimeMachines.length}>
          <MachineRanking data={data} />
        </Panel>
        <Panel title="Operational summary" subtitle="Current network snapshot">
          <div className="summary-list">
            <SummaryRow icon={<Factory size={16} />} label="Production facilities" value={new Set(data.lines.map((line) => line.factory_name)).size} tone="blue" />
            <SummaryRow icon={<CircleGauge size={16} />} label="Active production lines" value={data.lines.length} tone="green" />
            <SummaryRow icon={<Wrench size={16} />} label="Tracked machines" value={data.machines.length} tone="amber" />
            <SummaryRow icon={<Activity size={16} />} label="Downtime events" value={data.downtimeCauses.reduce((sum, item) => sum + item.event_count, 0)} tone="red" />
          </div>
          <div className="summary-footnote">Metrics are calculated from recorded simulated manufacturing data.</div>
        </Panel>
      </div>
    </>
  );
}

function SummaryRow({ icon, label, value, tone }: { icon: ReactNode; label: string; value: number; tone: string }) {
  return (
    <div className="summary-row">
      <span className={`summary-icon summary-${tone}`}>{icon}</span>
      <span>{label}</span>
      <strong>{quantity(value)}</strong>
    </div>
  );
}

export function ProductionPage({ data, loading }: { data: DashboardData; loading: boolean }) {
  return (
    <>
      <div className="page-intro-row"><div><h2>Production analysis</h2><p>Daily output and target performance by production line.</p></div></div>
      <div className="dashboard-grid">
        <Panel title="Daily production trends" subtitle="Actual units and production target by day" className="panel-span-two" loading={loading} error={endpointError(data, "trends")} empty={!data.trends.length}>
          <div className="chart-area chart-tall"><TrendChart data={data} /></div>
        </Panel>
        <Panel title="Line attainment" subtitle="Actual production as a share of target" loading={loading} error={endpointError(data, "lines")} empty={!data.lines.length}>
          <div className="chart-area chart-tall"><LineChart data={data} /></div>
        </Panel>
      </div>
      <Panel title="Production-line performance" subtitle="Actual units, target, attainment, and unplanned downtime" loading={loading} error={endpointError(data, "lines")} empty={!data.lines.length}>
        <ProductionTable data={data} />
      </Panel>
    </>
  );
}

export function DowntimePage({ data, loading }: { data: DashboardData; loading: boolean }) {
  return (
    <>
      <div className="page-intro-row"><div><h2>Downtime analysis</h2><p>Lost production time, grouped by operational cause and machine.</p></div></div>
      <div className="dashboard-grid">
        <Panel title="Downtime by cause" subtitle="Planned and unplanned events from recorded downtime" className="panel-span-two" loading={loading} error={endpointError(data, "downtimeCauses")} empty={!data.downtimeCauses.length}>
          <div className="chart-area chart-tall"><CauseChart data={data} /></div>
        </Panel>
        <Panel title="Downtime by classification" subtitle="Event mix from recorded events" loading={loading} error={endpointError(data, "downtimeCauses")} empty={!data.downtimeCauses.length}>
          <div className="classification-list">
            {(["Unplanned", "Planned"] as const).map((label) => {
              const planned = label === "Planned";
              const events = data.downtimeCauses.filter((item) => item.is_planned === planned);
              const minutes = events.reduce((total, item) => total + item.downtime_minutes, 0);
              const count = events.reduce((total, item) => total + item.event_count, 0);
              return <div className="classification-card" key={label}><span className={`classification-dot ${planned ? "dot-blue" : "dot-amber"}`} /><div><span>{label}</span><strong>{duration(minutes)}</strong></div><small>{quantity(count)} events</small></div>;
            })}
          </div>
        </Panel>
      </div>
      <Panel title="Machine downtime ranking" subtitle="Machines ranked by accumulated unplanned downtime" loading={loading} error={endpointError(data, "downtimeMachines")} empty={!data.downtimeMachines.length}>
        <MachineRanking data={data} limit={data.downtimeMachines.length} />
      </Panel>
    </>
  );
}

export function QualityPage({ data, loading }: { data: DashboardData; loading: boolean }) {
  const inspected = data.qualityLines.reduce((sum, line) => sum + line.inspected_units, 0);
  const defective = data.qualityLines.reduce((sum, line) => sum + line.defective_units, 0);
  const overallRate = inspected ? (defective / inspected) * 100 : null;
  return (
    <>
      <div className="page-intro-row"><div><h2>Quality performance</h2><p>Inspection coverage and recorded defects by production line.</p></div></div>
      <div className="kpi-grid kpi-grid-three">
        <KpiCard label="Units inspected" value={quantity(inspected)} detail="Across all recorded inspections" icon={<CheckCircle2 size={19} />} tone="blue" />
        <KpiCard label="Defective units" value={quantity(defective)} detail="Recorded inspection findings" icon={<AlertTriangle size={19} />} tone="red" />
        <KpiCard label="Overall defect rate" value={percent(overallRate)} detail="Defective units ÷ inspected units" icon={<Target size={19} />} tone="amber" />
      </div>
      <Panel title="Defect rate by production line" subtitle="Defective inspected units as a share of inspected units" loading={loading} error={endpointError(data, "qualityLines")} empty={!data.qualityLines.length}>
        <QualityTable data={data} />
      </Panel>
    </>
  );
}

export function MachinesPage({ data, loading }: { data: DashboardData; loading: boolean }) {
  return (
    <>
      <div className="page-intro-row"><div><h2>Machine directory</h2><p>Operational metrics and production-line relationships for tracked machines.</p></div><span className="data-range">{quantity(data.machines.length)} machines</span></div>
      <Panel title="Machine performance" subtitle="Production, target attainment, downtime, and inspection metrics" loading={loading} error={endpointError(data, "machines")} empty={!data.machines.length} className="machine-panel">
        <MachinesTable data={data} />
      </Panel>
    </>
  );
}
