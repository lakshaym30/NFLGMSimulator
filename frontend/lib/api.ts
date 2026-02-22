const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(
      `Request to ${path} failed with ${response.status} ${
        response.statusText
      }${detail ? ` — ${detail}` : ""}`,
    );
  }
  return (await response.json()) as T;
}

export type TeamSummary = {
  code: string;
  display_name: string;
  short_display_name: string | null;
  location: string | null;
  nickname: string | null;
  logo: string | null;
};

export type TeamListResponse = {
  teams: TeamSummary[];
};

export type PlayerContract = {
  id: number;
  source: string;
  source_url: string | null;
  signed_date: string | null;
  total_value: number | null;
  guaranteed: number | null;
  average_per_year: number | null;
  notes: string | null;
};

export type PlayerSummary = {
  id: number;
  external_id: string;
  team_code: string;
  first_name: string;
  last_name: string;
  full_name: string;
  position: string;
  jersey_number: number | null;
  status: string;
  experience: number;
  college: string | null;
  height: string | null;
  weight: number | null;
  birthdate: string | null;
  roster_date: string | null;
  roster_source: string | null;
  contract: PlayerContract | null;
};

export type TeamRosterResponse = {
  team: TeamSummary;
  roster_source: string | null;
  roster_date: string | null;
  player_count: number;
  players: PlayerSummary[];
};

export type PlayerDetailResponse = {
  team: TeamSummary;
  player: PlayerSummary;
  contracts: PlayerContract[];
};

export type CapEntry = {
  player_id: number;
  player_name: string;
  position: string;
  cap_hit: number;
  contract_id: number | null;
};

export type TeamCapResponse = {
  team: TeamSummary;
  cap_limit: number;
  total_cap_hit: number;
  cap_space: number;
  player_count: number;
  considered_player_count: number;
  top51_applied: boolean;
  entries: CapEntry[];
};

export function fetchTeams() {
  return getJson<TeamListResponse>("/teams");
}

export function fetchTeamRoster(teamCode: string) {
  return getJson<TeamRosterResponse>(`/teams/${teamCode}/roster`);
}

export function fetchTeamCap(teamCode: string, options?: { top51?: boolean }) {
  const params = new URLSearchParams();
  if (options?.top51 === false) {
    params.set("top51", "false");
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return getJson<TeamCapResponse>(`/teams/${teamCode}/cap${suffix}`);
}

export function fetchPlayerDetail(playerId: number) {
  return getJson<PlayerDetailResponse>(`/players/${playerId}`);
}

export type TransactionType = "release" | "sign" | "trade";

export type TransactionRequest = {
  team_code: string;
  type: TransactionType;
  payload: Record<string, any>;
};

export type TransactionPreview = {
  allowed: boolean;
  type: TransactionType;
  team: string;
  cap_limit: number;
  total_cap: number;
  cap_space_before: number;
  cap_space_after: number;
  cap_delta: number;
  dead_money: number;
  dead_money_future: number;
  roster_delta: number;
  roster_count_after: number;
  notes: string[];
  payload: Record<string, any>;
};

export type TransactionRecord = {
  id: number;
  type: TransactionType;
  team: TeamSummary;
  cap_delta: number;
  cap_space_after: number;
  payload: Record<string, any>;
  notes: string[];
  status: string;
  created_at: string;
};

export function previewTransaction(body: TransactionRequest) {
  return fetch(`${API_BASE}/transactions/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(async (response) => {
    if (!response.ok) {
      const detail = await response.text().catch(() => "");
      throw new Error(
        detail || `Preview failed (${response.status} ${response.statusText})`,
      );
    }
    return (await response.json()) as TransactionPreview;
  });
}

export function commitTransaction(body: TransactionRequest) {
  return fetch(`${API_BASE}/transactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(async (response) => {
    if (!response.ok) {
      const detail = await response.text().catch(() => "");
      throw new Error(
        detail || `Transaction failed (${response.status} ${response.statusText})`,
      );
    }
    return (await response.json()) as TransactionRecord;
  });
}

export function fetchTransactions(teamCode?: string, limit = 10) {
  const params = new URLSearchParams();
  if (teamCode) params.set("team_code", teamCode);
  if (limit) params.set("limit", String(limit));
  const query = params.toString();
  const url = query ? `/transactions?${query}` : "/transactions";
  return getJson<TransactionRecord[]>(url);
}

export function undoTransaction(id: number) {
  return fetch(`${API_BASE}/transactions/${id}/undo`, {
    method: "POST",
  }).then(async (response) => {
    if (!response.ok) {
      const detail = await response.text().catch(() => "");
      throw new Error(
        detail || `Undo failed (${response.status} ${response.statusText})`,
      );
    }
    return (await response.json()) as TransactionRecord;
  });
}

export type Prospect = {
  id: number;
  name: string;
  position: string;
  school: string;
  grade: number;
  archetype?: string;
};

export type ProspectBoard = {
  class_year: number;
  source?: string;
  prospects: Prospect[];
};

export function fetchProspects() {
  return getJson<ProspectBoard>("/draft/prospects");
}

export type DraftSimulation = {
  team: string;
  rounds: number;
  picks: Array<{ overall: number; round: number; team: string; prospect: Prospect }>;
  team_picks: Array<{ overall: number; round: number; team: string; prospect: Prospect }>;
  prospects_remaining: Prospect[];
};

export function simulateDraft(teamCode: string, rounds = 7) {
  return fetch(`${API_BASE}/draft/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ team_code: teamCode, rounds }),
  }).then(async (response) => {
    if (!response.ok) {
      const detail = await response.text().catch(() => "");
      throw new Error(detail || `Draft sim failed (${response.status})`);
    }
    return (await response.json()) as DraftSimulation;
  });
}

export type SeasonGame = {
  week: number;
  home: boolean;
  opponent: string;
  team_score: number;
  opponent_score: number;
  result: string;
};

export type SeasonSimulation = {
  team: string;
  standings: { team: string; wins: number; losses: number; ties: number };
  schedule: SeasonGame[];
  conference: Record<string, Array<{ team: string; wins: number; losses: number; ties: number }>>;
};

export function simulateSeason(teamCode: string, weeks = 17) {
  return fetch(`${API_BASE}/season/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ team_code: teamCode, weeks }),
  }).then(async (response) => {
    if (!response.ok) {
      const detail = await response.text().catch(() => "");
      throw new Error(detail || `Season sim failed (${response.status})`);
    }
    return (await response.json()) as SeasonSimulation;
  });
}

export type FreeAgentProfile = {
  id: string;
  name: string;
  position: string;
  age: number | null;
  market_value: number | null;
  traits: string[];
  preferred_roles: string[];
  last_team: string | null;
  preferred_years: number[];
  scheme_fits: string[];
  fit_score: number;
  contender_score: number;
  value_score: number;
  notes: string[];
};

export type FreeAgentListResponse = {
  free_agents: FreeAgentProfile[];
};

export function fetchFreeAgents(teamCode: string) {
  return getJson<FreeAgentListResponse>(`/market/free-agents?team_code=${teamCode}`);
}

export type TradeTargetProfile = {
  player_id: number;
  name: string;
  position: string;
  team: { code: string; display_name?: string; logo?: string | null };
  cap_hit: number;
  years_remaining: number;
  fit_score: number;
  availability_score: number;
  contender_score: number;
  notes: string[];
};

export type TradeTargetResponse = {
  trade_targets: TradeTargetProfile[];
};

export function fetchTradeTargets(teamCode: string) {
  return getJson<TradeTargetResponse>(`/market/trade-targets?team_code=${teamCode}`);
}

export type FreeAgentOfferRequest = {
  type: "free_agent";
  team_code: string;
  free_agent_id: string;
  years: number;
  apy: number;
  signing_bonus: number;
  roster_bonus: number;
  workout_bonus: number;
};

export type TradeOfferRequest = {
  type: "trade";
  team_code: string;
  partner_team_code: string;
  send_player_ids: number[];
  receive_player_ids: number[];
  post_june_1?: boolean;
};

export type MarketOfferRequest = FreeAgentOfferRequest | TradeOfferRequest;

export type MarketOfferResponse = {
  accepted: boolean;
  type: "free_agent" | "trade";
  notes: string[];
  counter?: Record<string, any>;
  cap_space_after?: number;
  transaction_id?: number;
};

export function submitMarketOffer(body: MarketOfferRequest) {
  return fetch(`${API_BASE}/market/offers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(async (response) => {
    if (!response.ok) {
      const detail = await response.text().catch(() => "");
      throw new Error(detail || `Offer failed (${response.status} ${response.statusText})`);
    }
    return (await response.json()) as MarketOfferResponse;
  });
}
