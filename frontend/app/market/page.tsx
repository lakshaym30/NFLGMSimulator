"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  FreeAgentProfile,
  MarketOfferResponse,
  PlayerSummary,
  TeamCapResponse,
  TeamSummary,
  TradeTargetProfile,
  fetchFreeAgents,
  fetchTeamCap,
  fetchTeamRoster,
  fetchTeams,
  fetchTradeTargets,
  submitMarketOffer,
} from "../../lib/api";

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function formatMoney(value?: number | null) {
  if (value === undefined || value === null) return "–";
  return currency.format(value);
}

type AlertState = { tone: "success" | "error"; message: string; notes?: string[] };

export default function MarketPage() {
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [teamCode, setTeamCode] = useState<string>("ARI");
  const [cap, setCap] = useState<TeamCapResponse | null>(null);
  const [roster, setRoster] = useState<PlayerSummary[]>([]);
  const [freeAgents, setFreeAgents] = useState<FreeAgentProfile[]>([]);
  const [tradeTargets, setTradeTargets] = useState<TradeTargetProfile[]>([]);
  const [activeTab, setActiveTab] = useState<"free_agents" | "trade_machine">("free_agents");
  const [loading, setLoading] = useState(false);
  const [faOfferState, setFaOfferState] = useState({
    years: 3,
    apy: 15000000,
    signing_bonus: 4000000,
    roster_bonus: 1000000,
    workout_bonus: 250000,
  });
  const [selectedFreeAgent, setSelectedFreeAgent] = useState<string | null>(null);
  const [faAlert, setFaAlert] = useState<AlertState | null>(null);

  const [selectedTradeTargets, setSelectedTradeTargets] = useState<number[]>([]);
  const [sendPlayerIds, setSendPlayerIds] = useState<number[]>([]);
  const [tradeAlert, setTradeAlert] = useState<AlertState | null>(null);
  const [tradeLoading, setTradeLoading] = useState(false);

  useEffect(() => {
    async function bootstrap() {
      try {
        const list = await fetchTeams();
        setTeams(list.teams);
        setTeamCode((list.teams.find((t) => t.code === "ARI") ?? list.teams[0])?.code ?? "ARI");
      } catch (error) {
        console.warn("Unable to fetch teams", error);
      }
    }
    void bootstrap();
  }, []);

  useEffect(() => {
    if (!teamCode) return;
    async function loadTeam() {
      setLoading(true);
      try {
        const [capResp, rosterResp, faResp, tradeResp] = await Promise.all([
          fetchTeamCap(teamCode),
          fetchTeamRoster(teamCode),
          fetchFreeAgents(teamCode),
          fetchTradeTargets(teamCode),
        ]);
        setCap(capResp);
        setRoster(rosterResp.players);
        setFreeAgents(faResp.free_agents);
        setTradeTargets(tradeResp.trade_targets);
        setSelectedFreeAgent((prev) => prev ?? faResp.free_agents[0]?.id ?? null);
        setSelectedTradeTargets([]);
        setSendPlayerIds([]);
      } catch (error) {
        console.warn("Unable to load market data", error);
      } finally {
        setLoading(false);
      }
    }
    void loadTeam();
  }, [teamCode]);

  const selectedFreeAgentProfile = useMemo(() => {
    if (!selectedFreeAgent) return freeAgents[0];
    return freeAgents.find((agent) => agent.id === selectedFreeAgent) ?? freeAgents[0];
  }, [selectedFreeAgent, freeAgents]);

  const partnerTeam = useMemo(() => {
    if (!selectedTradeTargets.length) return null;
    const first = tradeTargets.find((target) => target.player_id === selectedTradeTargets[0]);
    return first?.team ?? null;
  }, [selectedTradeTargets, tradeTargets]);

  async function handleFreeAgentOffer() {
    const target = selectedFreeAgentProfile;
    if (!target) return;
    setFaAlert(null);
    try {
      const response = await submitMarketOffer({
        type: "free_agent",
        team_code: teamCode,
        free_agent_id: target.id,
        years: faOfferState.years,
        apy: faOfferState.apy,
        signing_bonus: faOfferState.signing_bonus,
        roster_bonus: faOfferState.roster_bonus,
        workout_bonus: faOfferState.workout_bonus,
      });
      await refreshAfterOffer(response, "free_agent");
      setFaAlert({
        tone: response.accepted ? "success" : "error",
        message: response.accepted
          ? `${target.name} accepted your offer.`
          : `${target.name} declined.`,
        notes: response.notes,
      });
    } catch (error) {
      setFaAlert({
        tone: "error",
        message: error instanceof Error ? error.message : "Offer failed",
      });
    }
  }

  async function handleTradeOffer() {
    if (!partnerTeam) {
      setTradeAlert({
        tone: "error",
        message: "Select at least one trade target to choose a partner team.",
      });
      return;
    }
    if (!sendPlayerIds.length) {
      setTradeAlert({
        tone: "error",
        message: "Pick at least one player to send in the deal.",
      });
      return;
    }
    setTradeLoading(true);
    setTradeAlert(null);
    try {
      const response = await submitMarketOffer({
        type: "trade",
        team_code: teamCode,
        partner_team_code: partnerTeam.code,
        send_player_ids: sendPlayerIds,
        receive_player_ids: selectedTradeTargets,
        post_june_1: false,
      });
      await refreshAfterOffer(response, "trade");
      setTradeAlert({
        tone: response.accepted ? "success" : "error",
        message: response.accepted
          ? "Trade executed successfully."
          : "Trade declined by AI front office.",
        notes: response.notes,
      });
      if (response.accepted) {
        setSelectedTradeTargets([]);
        setSendPlayerIds([]);
      }
    } catch (error) {
      setTradeAlert({
        tone: "error",
        message: error instanceof Error ? error.message : "Trade failed",
      });
    } finally {
      setTradeLoading(false);
    }
  }

  async function refreshAfterOffer(response: MarketOfferResponse, type: "free_agent" | "trade") {
    if (!response.accepted) return;
    const [capResp, rosterResp, faResp, tradeResp] = await Promise.all([
      fetchTeamCap(teamCode),
      fetchTeamRoster(teamCode),
      fetchFreeAgents(teamCode),
      fetchTradeTargets(teamCode),
    ]);
    setCap(capResp);
    setRoster(rosterResp.players);
    setFreeAgents(faResp.free_agents);
    setTradeTargets(tradeResp.trade_targets);
    if (type === "free_agent") {
      setSelectedFreeAgent(faResp.free_agents[0]?.id ?? null);
    } else {
      setSelectedTradeTargets([]);
      setSendPlayerIds([]);
    }
  }

  const rosterByPosition = useMemo(() => {
    const grouped: Record<string, PlayerSummary[]> = {};
    roster.forEach((player) => {
      grouped[player.position] = grouped[player.position] || [];
      grouped[player.position].push(player);
    });
    return grouped;
  }, [roster]);

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-10">
        <header className="space-y-4 rounded-2xl border border-slate-900/80 bg-slate-950/60 p-6 shadow-lg shadow-black/30">
          <p className="text-xs uppercase tracking-[0.3em] text-cardinalsSand">
            League marketplace
          </p>
          <div className="flex flex-col items-start gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h1 className="text-3xl font-semibold">Negotiation Hub</h1>
              <p className="text-sm text-slate-300">
                Scout free agents, build trade proposals, and let the AI front offices respond in
                real time.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <select
                value={teamCode}
                onChange={(event) => setTeamCode(event.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              >
                {teams.map((team) => (
                  <option key={team.code} value={team.code}>
                    {team.display_name}
                  </option>
                ))}
              </select>
              <Link
                href="/"
                className="rounded-full border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-100 hover:border-cardinalsSand/60"
              >
                ← Back to dashboard
              </Link>
            </div>
          </div>
          <div className="grid gap-4 text-sm text-slate-300 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-900/60 bg-slate-900/30 p-4">
              <p className="text-xs uppercase tracking-widest text-slate-500">Cap Space</p>
              <p className="text-2xl text-cardinalsSand">
                {cap ? formatMoney(cap.cap_space) : "Loading…"}
              </p>
              <p className="text-xs text-slate-500">
                Limit: {cap ? formatMoney(cap.cap_limit) : "Loading…"}
              </p>
            </div>
            <div className="rounded-xl border border-slate-900/60 bg-slate-900/30 p-4">
              <p className="text-xs uppercase tracking-widest text-slate-500">Roster Count</p>
              <p className="text-2xl">{roster.length || "–"}</p>
              <p className="text-xs text-slate-500">Target: 90 offseason</p>
            </div>
            <div className="rounded-xl border border-slate-900/60 bg-slate-900/30 p-4">
              <p className="text-xs uppercase tracking-widest text-slate-500">Status</p>
              <p className="text-2xl">{loading ? "Refreshing…" : "Ready"}</p>
              <p className="text-xs text-slate-500">
                AI scorecards refresh whenever you reload this page.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              className={`rounded-full px-4 py-2 text-sm font-semibold ${
                activeTab === "free_agents"
                  ? "bg-cardinalsRed text-white shadow-lg shadow-cardinalsRed/40"
                  : "border border-slate-700 text-slate-200 hover:border-cardinalsSand/60"
              }`}
              onClick={() => setActiveTab("free_agents")}
            >
              Free Agency Board
            </button>
            <button
              type="button"
              className={`rounded-full px-4 py-2 text-sm font-semibold ${
                activeTab === "trade_machine"
                  ? "bg-cardinalsRed text-white shadow-lg shadow-cardinalsRed/40"
                  : "border border-slate-700 text-slate-200 hover:border-cardinalsSand/60"
              }`}
              onClick={() => setActiveTab("trade_machine")}
            >
              Trade Machine
            </button>
          </div>
        </header>

        {activeTab === "free_agents" ? (
          <section className="grid gap-6 lg:grid-cols-[2fr,1fr]">
            <div className="space-y-4">
              {freeAgents.map((agent) => (
                <button
                  key={agent.id}
                  type="button"
                  onClick={() => setSelectedFreeAgent(agent.id)}
                  className={`flex w-full flex-col gap-2 rounded-2xl border p-4 text-left transition ${
                    selectedFreeAgentProfile?.id === agent.id
                      ? "border-cardinalsSand/60 bg-slate-900/60"
                      : "border-slate-900/70 bg-slate-900/20 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-lg font-semibold text-white">{agent.name}</p>
                      <p className="text-xs uppercase tracking-widest text-slate-500">
                        {agent.position} · Fit {agent.fit_score} / Value {agent.value_score}
                      </p>
                    </div>
                    <p className="text-sm text-cardinalsSand">
                      {agent.market_value ? `${formatMoney(agent.market_value)}/yr` : "N/A"}
                    </p>
                  </div>
                  <p className="text-sm text-slate-300">{agent.traits.join(" · ")}</p>
                  <p className="text-xs text-slate-500">{agent.notes.join(" ")} </p>
                </button>
              ))}
              {freeAgents.length === 0 && (
                <p className="text-sm text-slate-400">Marketplace is empty. Import free agents to continue.</p>
              )}
            </div>
            <div className="space-y-4 rounded-2xl border border-slate-900/60 bg-slate-900/40 p-5">
              <h2 className="text-xl font-semibold">Offer Builder</h2>
              {selectedFreeAgentProfile ? (
                <>
                  <div>
                    <p className="text-sm text-slate-400">Target</p>
                    <p className="text-lg font-semibold">
                      {selectedFreeAgentProfile.name} · {selectedFreeAgentProfile.position}
                    </p>
                  </div>
                  <label className="flex flex-col gap-1 text-sm">
                    Years {faOfferState.years}
                    <input
                      type="range"
                      min={1}
                      max={6}
                      value={faOfferState.years}
                      onChange={(event) =>
                        setFaOfferState((state) => ({
                          ...state,
                          years: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-sm">
                    APY ({formatMoney(faOfferState.apy)})
                    <input
                      type="number"
                      min={1000000}
                      step={500000}
                      value={faOfferState.apy}
                      onChange={(event) =>
                        setFaOfferState((state) => ({
                          ...state,
                          apy: Number(event.target.value),
                        }))
                      }
                      className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2"
                    />
                  </label>
                  <div className="grid gap-3 sm:grid-cols-3">
                    {(["signing_bonus", "roster_bonus", "workout_bonus"] as const).map((field) => (
                      <label key={field} className="flex flex-col gap-1 text-sm">
                        {field.replace("_", " ")}
                        <input
                          type="number"
                          min={0}
                          step={250000}
                          value={faOfferState[field]}
                          onChange={(event) =>
                            setFaOfferState((state) => ({
                              ...state,
                              [field]: Number(event.target.value),
                            }))
                          }
                          className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2"
                        />
                      </label>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleFreeAgentOffer()}
                    className="w-full rounded-full bg-cardinalsRed px-4 py-2 text-center text-sm font-semibold text-white shadow-lg shadow-cardinalsRed/40 disabled:opacity-50"
                    disabled={!selectedFreeAgentProfile}
                  >
                    Submit Offer
                  </button>
                  {faAlert && (
                    <div
                      className={`rounded-xl border p-3 text-sm ${
                        faAlert.tone === "success"
                          ? "border-emerald-400/40 bg-emerald-950/40 text-emerald-200"
                          : "border-red-400/40 bg-red-950/40 text-red-200"
                      }`}
                    >
                      <p className="font-semibold">{faAlert.message}</p>
                      {faAlert.notes && (
                        <ul className="mt-2 list-disc space-y-1 pl-4">
                          {faAlert.notes.map((note) => (
                            <li key={note}>{note}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-slate-400">Select a free agent to begin crafting offers.</p>
              )}
            </div>
          </section>
        ) : (
          <section className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-3 rounded-2xl border border-slate-900/70 bg-slate-900/30 p-5">
              <h2 className="text-xl font-semibold">Targets ({tradeTargets.length})</h2>
              <div className="max-h-[600px] space-y-3 overflow-y-auto pr-1">
                {tradeTargets.map((target) => (
                  <label
                    key={target.player_id}
                    className={`flex cursor-pointer flex-col gap-1 rounded-xl border p-3 text-sm transition ${
                      selectedTradeTargets.includes(target.player_id)
                        ? "border-cardinalsSand/60 bg-slate-900/60"
                        : "border-slate-900/70 bg-slate-900/20 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="font-semibold text-white">{target.name}</p>
                        <p className="text-xs uppercase tracking-widest text-slate-500">
                          {target.team.code} · {target.position} · Fit {target.fit_score}
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={selectedTradeTargets.includes(target.player_id)}
                        onChange={(event) => {
                          setSelectedTradeTargets((current) =>
                            event.target.checked
                              ? [...current, target.player_id]
                              : current.filter((id) => id !== target.player_id),
                          );
                        }}
                      />
                    </div>
                    <p className="text-xs text-slate-400">
                      Cap hit {formatMoney(target.cap_hit)} · Availability {target.availability_score}
                    </p>
                    <p className="text-xs text-slate-500">{target.notes.join(" ")}</p>
                  </label>
                ))}
                {tradeTargets.length === 0 && (
                  <p className="text-sm text-slate-400">No suitable partners detected.</p>
                )}
              </div>
            </div>
            <div className="space-y-4 rounded-2xl border border-slate-900/70 bg-slate-900/30 p-5">
              <h2 className="text-xl font-semibold">Trade Composer</h2>
              <div>
                <p className="text-sm text-slate-400">Partner</p>
                <p className="text-lg font-semibold">
                  {partnerTeam ? partnerTeam.display_name ?? partnerTeam.code : "Select a target"}
                </p>
              </div>
              <label className="flex flex-col gap-1 text-sm">
                Players to send ({sendPlayerIds.length})
                <select
                  multiple
                  value={sendPlayerIds.map(String)}
                  onChange={(event) => {
                    const selected = Array.from(event.target.selectedOptions).map((option) =>
                      Number(option.value),
                    );
                    setSendPlayerIds(selected);
                  }}
                  className="h-40 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm"
                >
                  {roster.map((player) => (
                    <option key={player.id} value={player.id}>
                      {player.full_name} — {player.position} ({player.contract?.average_per_year
                        ? formatMoney(player.contract.average_per_year)
                        : "no deal"})
                    </option>
                  ))}
                </select>
              </label>
              <p className="text-xs text-slate-500">
                Roster balance snapshot:{" "}
                {Object.entries(rosterByPosition)
                  .map(([position, players]) => `${position}:${players.length}`)
                  .join(" · ")}
              </p>
              <button
                type="button"
                onClick={() => void handleTradeOffer()}
                disabled={!selectedTradeTargets.length || !sendPlayerIds.length || tradeLoading}
                className="w-full rounded-full bg-cardinalsRed px-4 py-2 text-center text-sm font-semibold text-white shadow-lg shadow-cardinalsRed/40 disabled:opacity-40"
              >
                {tradeLoading ? "Submitting…" : "Submit Proposal"}
              </button>
              {tradeAlert && (
                <div
                  className={`rounded-xl border p-3 text-sm ${
                    tradeAlert.tone === "success"
                      ? "border-emerald-400/40 bg-emerald-950/40 text-emerald-200"
                      : "border-red-400/40 bg-red-950/40 text-red-200"
                  }`}
                >
                  <p className="font-semibold">{tradeAlert.message}</p>
                  {tradeAlert.notes && (
                    <ul className="mt-2 list-disc space-y-1 pl-4">
                      {tradeAlert.notes.map((note) => (
                        <li key={note}>{note}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
