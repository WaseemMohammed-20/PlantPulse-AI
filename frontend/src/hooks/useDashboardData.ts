import { useCallback, useEffect, useState } from "react";
import { loadDashboardData, type GetAuthToken } from "../api/client";
import { demoDashboardData } from "../demoData";
import type { DashboardData } from "../types";

export function useDashboardData(
  getAuthToken: GetAuthToken,
  forceDemoMode = false,
) {
  const [data, setData] = useState<DashboardData>(demoDashboardData);
  const [loading, setLoading] = useState(false);
  const [demoMode, setDemoMode] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    if (forceDemoMode) {
      setData(demoDashboardData);
      setDemoMode(true);
      setLoading(false);
      return () => {
        active = false;
      };
    }

    loadDashboardData(getAuthToken)
      .then((result) => {
        if (!active) return;
        const isLive =
          result.health?.status === "ok" &&
          result.health.database === "connected" &&
          Object.keys(result.errors).length === 0;
        setData(isLive ? result : demoDashboardData);
        setDemoMode(!isLive);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [forceDemoMode, getAuthToken, refreshKey]);

  const refresh = useCallback(() => {
    setRefreshKey((key) => key + 1);
  }, []);

  return { data, loading, demoMode, refresh };
}
