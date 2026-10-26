import {
  Activity,
  Factory,
  Gauge,
  LayoutDashboard,
  Settings2,
  ShieldCheck,
  Wrench,
} from "lucide-react";
import type { PageName } from "../types";

const items: { label: PageName; icon: typeof LayoutDashboard }[] = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Production", icon: Gauge },
  { label: "Downtime", icon: Activity },
  { label: "Quality", icon: ShieldCheck },
  { label: "Machines", icon: Wrench },
];

interface SidebarProps {
  activePage: PageName;
  onNavigate: (page: PageName) => void;
}

export function Sidebar({ activePage, onNavigate }: SidebarProps) {
  return (
    <aside className="sidebar-shell">
      <div className="brand-lockup">
        <div className="brand-mark">
          <Factory size={21} strokeWidth={2.2} />
        </div>
        <div>
          <p className="brand-name">PlantPulse</p>
          <p className="brand-caption">MANUFACTURING INTELLIGENCE</p>
        </div>
      </div>

      <div className="nav-section-label">WORKSPACE</div>
      <nav className="sidebar-nav" aria-label="Main navigation">
        {items.map(({ label, icon: Icon }) => (
          <button
            aria-current={activePage === label ? "page" : undefined}
            className={`nav-item ${activePage === label ? "nav-item-active" : ""}`}
            key={label}
            onClick={() => onNavigate(label)}
            type="button"
          >
            <Icon size={18} strokeWidth={1.8} />
            <span>{label}</span>
            {label === "Overview" && <span className="nav-active-dot" />}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="plant-card">
          <div className="plant-card-icon">
            <Factory size={16} />
          </div>
          <div className="plant-card-copy">
            <span>Active workspace</span>
            <strong>All facilities</strong>
          </div>
          <Settings2 size={15} className="plant-card-settings" />
        </div>
        <div className="sidebar-user">
          <div className="user-avatar">PP</div>
          <div className="user-details">
            <strong>Plant operations</strong>
            <span>Analytics workspace</span>
          </div>
          <span className="user-menu">•••</span>
        </div>
      </div>
    </aside>
  );
}
