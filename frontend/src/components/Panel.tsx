import type { ReactNode } from "react";
import { AlertCircle, ArrowUpRight, LoaderCircle } from "lucide-react";

interface PanelProps {
  title: string;
  subtitle?: string;
  action?: string;
  onAction?: () => void;
  children: ReactNode;
  className?: string;
  loading?: boolean;
  error?: string;
  empty?: boolean;
  emptyMessage?: string;
}

export function Panel({
  title,
  subtitle,
  action,
  onAction,
  children,
  className = "",
  loading = false,
  error,
  empty = false,
  emptyMessage = "No data available for this period.",
}: PanelProps) {
  return (
    <section className={`panel-card ${className}`}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action && (
          <button className="panel-action" onClick={onAction} type="button">
            {action} <ArrowUpRight size={14} />
          </button>
        )}
      </div>
      <div className="panel-content">
        {loading ? (
          <div className="panel-state">
            <LoaderCircle size={22} className="spin" />
            <span>Loading data…</span>
          </div>
        ) : error ? (
          <div className="panel-state panel-error">
            <AlertCircle size={20} />
            <span>{error}</span>
          </div>
        ) : empty ? (
          <div className="panel-state">
            <span>{emptyMessage}</span>
          </div>
        ) : (
          children
        )}
      </div>
    </section>
  );
}
