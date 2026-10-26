import type {
  DashboardEndpoint,
  DashboardData,
  DowntimeCause,
  DowntimeMachine,
  HealthResponse,
  Machine,
  Overview,
  ProductionLine,
  ProductionTrend,
  QualityLine,
} from "../types";

const configuredApiUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const isLocalApiUrl =
  configuredApiUrl &&
  /^https?:\/\/(localhost|(?:[\w-]+\.)*localhost|127(?:\.\d{1,3}){3}|\[?::1\]?)(?::\d+)?(?:\/|$)/i.test(
    configuredApiUrl,
  );
const API_BASE_URL = (
  (configuredApiUrl && !(import.meta.env.PROD && isLocalApiUrl)
    ? configuredApiUrl
    : undefined) ||
  (import.meta.env.DEV ? "http://127.0.0.1:8000/api" : "/api")
).replace(/\/+$/, "");

export type GetAuthToken = () => Promise<string | null>;

async function getJson<T>(
  path: string,
  getAuthToken: GetAuthToken,
): Promise<T> {
  const token = path === "/health" ? null : await getAuthToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    signal: AbortSignal.timeout(5000),
    headers: {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!response.ok) {
    throw new Error(`API returned HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

function requestErrorMessage(error: unknown): string {
  if (error instanceof TypeError) {
    return `Network request failed. Check that ${API_BASE_URL} is reachable and CORS allows ${window.location.origin}.`;
  }
  return error instanceof Error ? error.message : "Unable to reach the API.";
}

const endpoints: {
  key: DashboardEndpoint;
  path: string;
  assign: (data: DashboardData, value: unknown) => void;
}[] = [
  {
    key: "health",
    path: "/health",
    assign: (data, value) => {
      data.health = value as HealthResponse;
    },
  },
  {
    key: "overview",
    path: "/overview",
    assign: (data, value) => {
      data.overview = value as Overview;
    },
  },
  {
    key: "trends",
    path: "/production/trends",
    assign: (data, value) => {
      data.trends = value as ProductionTrend[];
    },
  },
  {
    key: "lines",
    path: "/production/lines",
    assign: (data, value) => {
      data.lines = value as ProductionLine[];
    },
  },
  {
    key: "downtimeCauses",
    path: "/downtime/causes",
    assign: (data, value) => {
      data.downtimeCauses = value as DowntimeCause[];
    },
  },
  {
    key: "downtimeMachines",
    path: "/downtime/machines",
    assign: (data, value) => {
      data.downtimeMachines = value as DowntimeMachine[];
    },
  },
  {
    key: "qualityLines",
    path: "/quality/lines",
    assign: (data, value) => {
      data.qualityLines = value as QualityLine[];
    },
  },
  {
    key: "machines",
    path: "/machines",
    assign: (data, value) => {
      data.machines = value as Machine[];
    },
  },
];

export async function loadDashboardData(
  getAuthToken: GetAuthToken,
): Promise<DashboardData> {
  const data: DashboardData = {
    health: null,
    overview: null,
    trends: [],
    lines: [],
    downtimeCauses: [],
    downtimeMachines: [],
    qualityLines: [],
    machines: [],
    errors: {},
  };

  await Promise.all(
    endpoints.map(async ({ key, path, assign }) => {
      try {
        const value = await getJson<unknown>(path, getAuthToken);
        assign(data, value);
      } catch (error) {
        data.errors[key] = requestErrorMessage(error);
      }
    }),
  );
  return data;
}

export const apiBaseUrl = API_BASE_URL;
