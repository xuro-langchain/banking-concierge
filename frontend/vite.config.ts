import { defineConfig, loadEnv, type ProxyOptions } from "vite";
import react from "@vitejs/plugin-react";

// The agents the dev server can talk to, one per workspace. Each is proxied under
// /agents/<id>, with that workspace's API key added here, so no key reaches the browser.
function agents(env: Record<string, string>) {
  return [
    { id: "local", label: "Local (langgraph dev)", url: "http://localhost:2024", key: "" },
    { id: "robert", label: "Robert's Workspace", url: env.LANGGRAPH_DEPLOYMENT_URL, key: env.LANGSMITH_API_KEY },
    { id: "legacy", label: "Legacy Demo Workspace", url: env.LEGACY_DEPLOYMENT_URL, key: env.LEGACY_LANGSMITH_API_KEY },
  ].filter((a) => a.url);
}

// We serve the built bundle from the LangGraph agent server at `/concierge/`.
// Use a relative base so all asset URLs are sub-path safe.
export default defineConfig(({ command, mode }) => {
  const list = agents(loadEnv(mode, "..", ""));
  const proxy: Record<string, ProxyOptions> = {};
  for (const a of list) {
    proxy[`/agents/${a.id}`] = {
      target: a.url,
      changeOrigin: true,
      rewrite: (path) => path.replace(`/agents/${a.id}`, ""),
      configure: (p) =>
        p.on("proxyReq", (req) => {
          if (a.key) req.setHeader("x-api-key", a.key);
          else req.removeHeader("x-api-key");
        }),
    };
  }
  return {
    plugins: [react()],
    base: "./",
    // Labels only, and only on the dev server: a deployed build talks to its own origin.
    define: {
      __CONCIERGE_AGENTS__: JSON.stringify(
        command === "serve" ? list.map(({ id, label }) => ({ id, label })) : [],
      ),
    },
    server: { port: 5173, proxy },
    build: { outDir: "dist", emptyOutDir: true },
  };
});
