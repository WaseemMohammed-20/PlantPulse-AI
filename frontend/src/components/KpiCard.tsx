import type { ReactNode } from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

interface KpiCardProps {
  label: string;
  value: string;
  detail: string;
  icon: ReactNode;
  tone: "blue" | "green" | "amber" | "red";
  trend?: "up" | "down";
}

export function KpiCard({
  label,
  value,
  detail,
  icon,
  tone,
  trend,
}: KpiCardProps) {
  return (
    <article className="kpi-card">
      <div className="kpi-topline">
        <span className="kpi-label">{label}</span>
        <span className={`kpi-icon kpi-icon-${tone}`}>{icon}</span>
      </div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-detail">
        {trend === "up" && <ArrowUpRight size={14} className="trend-up" />}
        {trend === "down" && <ArrowDownRight size={14} className="trend-down" />}
        <span>{detail}</span>
      </div>
    </article>
  );
}
