import { useState } from "react";
import type { ReactNode } from "react";
import { Menu, X } from "lucide-react";
import { Header } from "./components/Header";
import { LoadingState } from "./components/LoadingState";
import { Sidebar } from "./components/Sidebar";
import { useDashboardData } from "./hooks/useDashboardData";
import {
  DowntimePage,
  MachinesPage,
  OverviewPage,
  ProductionPage,
  QualityPage,
} from "./pages/DashboardPages";
import type { PageName } from "./types";
import type { GetAuthToken } from "./api/client";

interface AppProps {
  getAuthToken: GetAuthToken;
  accountControls?: ReactNode;
  demoMode?: boolean;
}

function App({ getAuthToken, accountControls, demoMode = false }: AppProps) {
  const [page, setPage] = useState<PageName>("Overview");
  const [menuOpen, setMenuOpen] = useState(false);
  const {
    data,
    loading,
    demoMode: showingDemoData,
    refresh,
  } = useDashboardData(getAuthToken, demoMode);
  const connected = data.health?.status === "ok" && data.health.database === "connected";

  const navigate = (nextPage: PageName) => {
    setPage(nextPage);
    setMenuOpen(false);
  };

  const renderPage = () => {
    switch (page) {
      case "Production":
        return <ProductionPage data={data} loading={loading} />;
      case "Downtime":
        return <DowntimePage data={data} loading={loading} />;
      case "Quality":
        return <QualityPage data={data} loading={loading} />;
      case "Machines":
        return <MachinesPage data={data} loading={loading} />;
      default:
        return <OverviewPage data={data} loading={loading} />;
    }
  };

  return (
    <div className="app-shell">
      <div className={`sidebar-overlay ${menuOpen ? "overlay-visible" : ""}`} onClick={() => setMenuOpen(false)} />
      <div className={`sidebar-wrap ${menuOpen ? "sidebar-open" : ""}`}>
        <Sidebar activePage={page} onNavigate={navigate} />
      </div>
      <main className="main-shell">
        <div className="mobile-topbar">
          <button aria-label={menuOpen ? "Close navigation" : "Open navigation"} className="icon-button" onClick={() => setMenuOpen(!menuOpen)} type="button">
            {menuOpen ? <X size={19} /> : <Menu size={19} />}
          </button>
          <strong>PlantPulse <span>AI</span></strong>
        </div>
        <Header
          page={page}
          connected={connected}
          demoMode={showingDemoData}
          loading={loading}
          onRefresh={refresh}
          accountControls={accountControls}
        />
        <div className="content-area">
          {showingDemoData && (
            <div className="demo-banner" role="status">
              <strong>DEMO DATA</strong>
              <span>
                Showing simulated manufacturing records. This is not live
                production data.
              </span>
            </div>
          )}
          {loading ? (
            <LoadingState />
          ) : (
            <>
              {!connected && !showingDemoData && (
                <div className="connection-banner" role="status">
                  The API health check failed. Check the API address, database availability, and that CORS_ORIGINS includes this page's origin.
                  <button onClick={refresh} type="button">Retry</button>
                </div>
              )}
              {renderPage()}
            </>
          )}
          <footer className="page-footer">
            <span>PlantPulse AI <span className="footer-dot">·</span> Manufacturing Intelligence</span>
            <span>Simulated manufacturing data</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default App;
