/**
 * Which agent the UI talks to. On the dev server (`npm run dev`) there is a choice, one per
 * workspace, proxied by vite.config.ts under /agents/<id> with that workspace's key. A deployed
 * build has no list and talks to its own origin.
 */

export interface AgentChoice {
  id: string;
  label: string;
}

declare const __CONCIERGE_AGENTS__: AgentChoice[];

const STORAGE = "concierge:agent";

export const AGENTS: AgentChoice[] = typeof __CONCIERGE_AGENTS__ === "undefined" ? [] : __CONCIERGE_AGENTS__;

export function currentAgent(): AgentChoice | null {
  if (AGENTS.length === 0) return null;
  let saved: string | null = null;
  try {
    saved = window.localStorage.getItem(STORAGE);
  } catch {
    /* no storage: fall back to the first */
  }
  return AGENTS.find((a) => a.id === saved) ?? AGENTS[0];
}

export function chooseAgent(id: string): void {
  try {
    window.localStorage.setItem(STORAGE, id);
  } catch {
    /* ignore */
  }
  window.location.reload(); // threads belong to one agent, so start fresh
}

/** The base URL the SDK and API calls use. */
export function agentApiUrl(): string {
  const agent = currentAgent();
  return agent ? `${window.location.origin}/agents/${agent.id}` : window.location.origin;
}
