"use client";

import Link from "next/link";
import {
  fetchPlayerDetail,
  fetchTeamCap,
  fetchTeamRoster,
  fetchTeams,
  PlayerDetailResponse,
  PlayerSummary,
  TeamCapResponse,
  TeamRosterResponse,
  TeamSummary,
  TransactionRecord,
  fetchTransactions,
  undoTransaction,
} from "../lib/api";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { TeamPicker } from "../components/team-picker";
import { RosterTable, SortDirection, SortKey } from "../components/roster-table";
import { PlayerPanel } from "../components/player-panel";
import { TransactionPanel } from "../components/transaction-panel";
import { CapSummary } from "../components/cap-summary";
import { TransactionHistory } from "../components/transaction-history";
import { RosterInsights } from "../components/roster-insights";

const DEFAULT_TEAM = "ARI";

export default function HomePage() {
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const [roster, setRoster] = useState<TeamRosterResponse | null>(null);
  const [cap, setCap] = useState<TeamCapResponse | null>(null);
  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null);
  const [playerDetail, setPlayerDetail] = useState<PlayerDetailResponse | null>(
    null,
  );
  const [loadingRoster, setLoadingRoster] = useState(false);
  const [loadingPlayer, setLoadingPlayer] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [transactions, setTransactions] = useState<TransactionRecord[]>([]);
  const [loadingTransactions, setLoadingTransactions] = useState(false);
  const [useTop51, setUseTop51] = useState(true);

  const loadTransactions = useCallback(async (teamCode: string) => {
    setLoadingTransactions(true);
    try {
      const records = await fetchTransactions(teamCode, 10);
      setTransactions(records);
    } catch (err) {
      console.warn("Unable to load transactions", err);
    } finally {
      setLoadingTransactions(false);
    }
  }, []);

  const teamRequestRef = useRef(0);
  const playerRequestRef = useRef(0);

  const loadPlayerDetail = useCallback(async (playerId: number) => {
    const requestId = ++playerRequestRef.current;
    setLoadingPlayer(true);
    try {
      const detail = await fetchPlayerDetail(playerId);
      if (playerRequestRef.current === requestId) {
        setPlayerDetail(detail);
      }
    } catch (err) {
      if (playerRequestRef.current === requestId) {
        setPlayerDetail(null);
        setError(
          err instanceof Error ? err.message : "Failed to load player detail",
        );
      }
    } finally {
      if (playerRequestRef.current === requestId) {
        setLoadingPlayer(false);
      }
    }
  }, []);

  const loadTeamData = useCallback(
    async (teamCode: string) => {
      const requestId = ++teamRequestRef.current;
      setLoadingRoster(true);
      setError(null);

      try {
        const [rosterData, capData] = await Promise.all([
          fetchTeamRoster(teamCode),
          fetchTeamCap(teamCode, { top51: useTop51 }),
        ]);
        if (teamRequestRef.current !== requestId) {
          return;
        }
        setRoster(rosterData);
        setCap(capData);

        const defaultPlayer = rosterData.players[0];
        setSelectedPlayerId(defaultPlayer ? defaultPlayer.id : null);
        if (defaultPlayer) {
          await loadPlayerDetail(defaultPlayer.id);
        } else {
          setPlayerDetail(null);
        }
      } catch (err) {
        if (teamRequestRef.current === requestId) {
          setRoster(null);
          setCap(null);
          setPlayerDetail(null);
          setError(
            err instanceof Error ? err.message : "Failed to load team data",
          );
        }
      } finally {
        if (teamRequestRef.current === requestId) {
          setLoadingRoster(false);
        }
      }
    },
    [loadPlayerDetail, useTop51],
  );

  useEffect(() => {
    let mounted = true;
    async function bootstrap() {
      try {
        const payload = await fetchTeams();
        if (!mounted) return;
        setTeams(payload.teams);
        const preferredTeam =
          payload.teams.find((team) => team.code === DEFAULT_TEAM)?.code ??
          payload.teams[0]?.code ??
          null;
        setSelectedTeam(preferredTeam);
      } catch (err) {
        if (!mounted) return;
        setError(
          err instanceof Error ? err.message : "Failed to load team list",
        );
      }
    }
    void bootstrap();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedTeam) {
      return;
    }
    void (async () => {
      await loadTeamData(selectedTeam);
      await loadTransactions(selectedTeam);
    })();
  }, [selectedTeam, loadTeamData, loadTransactions]);

  const rosterPlayers: PlayerSummary[] = useMemo(
    () => roster?.players ?? [],
    [roster],
  );

  const capEntries = useMemo(() => cap?.entries ?? [], [cap]);


  const selectedPlayerSummary = useMemo(() => {
    if (!selectedPlayerId) return null;
    return rosterPlayers.find((p) => p.id === selectedPlayerId) ?? null;
  }, [selectedPlayerId, rosterPlayers]);

  const sortedPlayers = useMemo(() => {
    const data = [...rosterPlayers];
    const direction = sortDirection === "asc" ? 1 : -1;

    const getValue = (player: PlayerSummary) => {
      switch (sortKey) {
        case "name":
          return player.full_name.toLowerCase();
        case "position":
          return player.position;
        case "jersey":
          return player.jersey_number ?? 999;
        case "status":
          return player.status;
        case "experience":
          return player.experience;
        case "capHit":
          return player.contract?.average_per_year ?? 0;
        default:
          return player.full_name.toLowerCase();
      }
    };

    data.sort((a, b) => {
      const aValue = getValue(a);
      const bValue = getValue(b);

      if (typeof aValue === "number" && typeof bValue === "number") {
        return (aValue - bValue) * direction;
      }

      return String(aValue).localeCompare(String(bValue)) * direction;
    });

    return data;
  }, [rosterPlayers, sortDirection, sortKey]);

  const handleSortChange = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortDirection((prevDir) => (prevDir === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setSortDirection("asc");
      }
    },
    [sortKey],
  );

  const rosterMeta = useMemo(() => {
    if (!roster) {
      return null;
    }
    return {
      source: roster.roster_source ?? "Unknown",
      asOf: roster.roster_date
        ? new Date(roster.roster_date).toLocaleDateString()
        : "N/A",
      playerCount: roster.player_count,
    };
  }, [roster]);

  async function handlePlayerSelect(playerId: number) {
    setSelectedPlayerId(playerId);
    await loadPlayerDetail(playerId);
  }

  async function handleTransactionCommitted() {
    if (selectedTeam) {
      await loadTeamData(selectedTeam);
      await loadTransactions(selectedTeam);
    }
  }

  const handleUndoRelease = useCallback(
    async (transactionId: number) => {
      try {
        await undoTransaction(transactionId);
      } catch (error) {
        console.warn("Undo failed", error);
      } finally {
        if (selectedTeam) {
          await loadTeamData(selectedTeam);
          await loadTransactions(selectedTeam);
        }
      }
    },
    [selectedTeam, loadTeamData, loadTransactions],
  );


  return (
    <main className="min-h-screen bg-slate-950">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-10">
        <header className="flex flex-col gap-4 rounded-2xl border border-slate-900/80 bg-slate-950/70 p-6 shadow-lg shadow-black/20 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-4">
            <p className="text-xs uppercase tracking-[0.3em] text-cardinalsSand">
              Live league dashboard
            </p>
            <h1 className="text-3xl font-semibold text-white sm:text-4xl">
              NFL GM Control Room
            </h1>
            <p className="max-w-2xl text-sm text-slate-300 sm:text-base">
              Inspect any franchise roster, drill into player contracts, and
              monitor the salary cap without leaving the browser.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/gm-basics"
                className="rounded-full border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-100 hover:border-cardinalsSand/60"
              >
                Learn how the cap works
              </Link>
              <Link
                href="/draft"
                className="rounded-full border border-cardinalsSand/40 bg-cardinalsRed px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-cardinalsRed/40"
              >
                Open Draft Room
              </Link>
              <Link
                href="/market"
                className="rounded-full border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-100 hover:border-cardinalsSand/60"
              >
                Enter Marketplace
              </Link>
              <Link
                href="/season"
                className="rounded-full border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-100 hover:border-cardinalsSand/60"
              >
                Simulate a season
              </Link>
            </div>
          </div>
          <div className="w-full max-w-xs">
            <TeamPicker
              teams={teams}
              value={selectedTeam}
              onChange={(code) => setSelectedTeam(code)}
              disabled={!teams.length}
            />
          </div>
        </header>

        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-950/40 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        <section className="grid gap-6 lg:grid-cols-[2fr_1fr] items-start">
          <div className="space-y-6">
            <PlayerPanel detail={playerDetail} loading={loadingPlayer} />
            <TransactionPanel
              teamCode={selectedTeam}
              player={selectedPlayerSummary}
              onCommitted={handleTransactionCommitted}
            />

            <div className="flex flex-col gap-2 rounded-xl border border-slate-900/70 bg-slate-900/30 p-4 text-sm text-slate-300 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs uppercase tracking-widest text-slate-500">
                  Snapshot
                </p>
                <p>
                  Source: <span className="text-white">{rosterMeta?.source}</span>
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs uppercase tracking-widest text-slate-500">
                  As of
                </p>
                <p className="text-white">
                  {rosterMeta?.asOf ?? "Waiting for data"}
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs uppercase tracking-widest text-slate-500">
                  Players
                </p>
                <p className="text-white">{rosterMeta?.playerCount ?? "—"}</p>
              </div>
            </div>

            <RosterInsights players={rosterPlayers} capEntries={capEntries} />

            <RosterTable
              players={sortedPlayers}
              selectedPlayerId={selectedPlayerId}
              loading={loadingRoster}
              onSelect={(id) => void handlePlayerSelect(id)}
              sortKey={sortKey}
              sortDirection={sortDirection}
              onSortChange={handleSortChange}
            />
          </div>

          <div className="space-y-6">
            <div className="flex items-center justify-between rounded-xl border border-slate-900/60 bg-slate-900/30 px-4 py-2 text-sm text-slate-300">
              <div>
                <p className="text-xs uppercase tracking-widest text-slate-500">
                  Cap View Mode
                </p>
                <p>{useTop51 ? "Top-51 rule applied" : "All contracts counted"}</p>
              </div>
              <button
                type="button"
                onClick={() => setUseTop51((prev) => !prev)}
                className="rounded-full border border-slate-700 px-3 py-1 text-xs font-semibold text-white hover:border-cardinalsSand/60"
              >
                Toggle
              </button>
            </div>
            <CapSummary cap={cap} loading={loadingRoster} />
            <TransactionHistory
              transactions={transactions}
              loading={loadingTransactions}
              onUndo={handleUndoRelease}
            />
          </div>
        </section>
      </div>
    </main>
  );
}
