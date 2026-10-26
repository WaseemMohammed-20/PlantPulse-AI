import { Bell, CalendarDays, ChevronDown, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import type { PageName } from "../types";

interface HeaderProps {
  page: PageName;
  connected: boolean;
  demoMode: boolean;
  loading: boolean;
  onRefresh: () => void;
  accountControls?: ReactNode;
}

const descriptions: Record<PageName, string> = {
  Overview: "A clear view of production performance across your facilities.",
  Production: "Track output against target and compare line performance.",
  Downtime: "Understand lost production time and recurring causes.",
  Quality: "Monitor inspection outcomes and defects across production lines.",
  Machines: "Review machine-level performance and facility relationships.",
};

export function Header({
  page,
  connected,
  demoMode,
  loading,
  onRefresh,
  accountControls,
}: HeaderProps) {
  const today = new Intl.DateTimeFormat("en", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date());

  return (
    <header className="topbar">
      <div className="topbar-title">
        <div className="eyebrow">OPERATIONS / {page.toUpperCase()}</div>
        <h1>{page}</h1>
        <p>{descriptions[page]}</p>
      </div>
      <div className="topbar-actions">
        <div className={`connection-pill ${demoMode ? "is-demo" : connected ? "is-connected" : "is-disconnected"}`}>
          <span className="connection-dot" />
          {demoMode ? "Simulated demo" : connected ? "API connected" : "API unavailable"}
        </div>
        <div className="date-display">
          <CalendarDays size={16} />
          <span>{today}</span>
          <ChevronDown size={14} className="date-chevron" />
        </div>
        <button
          aria-label="Refresh dashboard data"
          className="icon-button"
          disabled={loading}
          onClick={onRefresh}
          title="Refresh data"
          type="button"
        >
          <RefreshCw size={17} className={loading ? "spin" : ""} />
        </button>
        <button aria-label="Notifications" className="icon-button notification-button" type="button">
          <Bell size={17} />
          <span />
        </button>
        {accountControls ?? <div className="header-avatar">DEMO</div>}
      </div>
    </header>
  );
}
