import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const apiBaseUrl = env.VITE_API_BASE_URL?.trim();
  const clerkPublishableKey = env.VITE_CLERK_PUBLISHABLE_KEY?.trim();
  const pointsToLocalApi =
    apiBaseUrl &&
    /^https?:\/\/(localhost|(?:[\w-]+\.)*localhost|127(?:\.\d{1,3}){3}|\[?::1\]?)(?::\d+)?(?:\/|$)/i.test(
      apiBaseUrl,
    );

  if (mode === "production" && pointsToLocalApi) {
    console.warn(
      "Ignoring the local development VITE_API_BASE_URL for production; the app will try same-origin /api and use simulated demo data when unavailable.",
    );
  }

  if (mode === "production" && apiBaseUrl && !pointsToLocalApi) {
    let apiUrl: URL;
    try {
      apiUrl = new URL(apiBaseUrl);
    } catch {
      throw new Error("Production VITE_API_BASE_URL must be an absolute HTTPS URL.");
    }

    if (
      apiUrl.protocol !== "https:" ||
      /^(localhost|(?:[\w-]+\.)*localhost|127(?:\.\d{1,3}){3}|\[?::1\]?)$/i.test(
        apiUrl.hostname,
      ) ||
      !apiUrl.pathname.replace(/\/+$/, "").endsWith("/api") ||
      apiUrl.username ||
      apiUrl.password ||
      apiUrl.search ||
      apiUrl.hash
    ) {
      throw new Error(
        "Production VITE_API_BASE_URL must be an external HTTPS API URL ending in /api, without credentials or query parameters.",
      );
    }
  }

  const productionDefines =
    mode === "production"
      ? {
          "import.meta.env.VITE_API_BASE_URL": JSON.stringify(
            pointsToLocalApi ? "" : apiBaseUrl ?? "",
          ),
          "import.meta.env.VITE_CLERK_PUBLISHABLE_KEY": JSON.stringify(
            clerkPublishableKey?.startsWith("pk_live_")
              ? clerkPublishableKey
              : "",
          ),
        }
      : undefined;

  return {
    define: productionDefines,
    plugins: [react(), tailwindcss()],
    server: {
      host: "localhost",
      port: 5173,
      strictPort: true,
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (
              id.includes("node_modules/recharts") ||
              id.includes("node_modules/d3-")
            ) {
              return "charts";
            }
            if (id.includes("node_modules/react")) {
              return "react-vendor";
            }
            if (id.includes("node_modules/lucide-react")) {
              return "icons";
            }
          },
        },
      },
    },
  };
});
