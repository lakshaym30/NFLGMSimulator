"use client";

import { useEffect, useState } from "react";
import {
  DraftSimulation,
  Prospect,
  ProspectBoard,
  TeamSummary,
  fetchProspects,
  fetchTeams,
  simulateDraft,
} from "../../lib/api";

export default function DraftPage() {
  const [board, setBoard] = useState<ProspectBoard | null>(null);
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string>("ARI");
  const [simulation, setSimulation] = useState<DraftSimulation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function bootstrap() {
      try {
        const [boardData, teamData] = await Promise.all([
          fetchProspects(),
          fetchTeams(),
        ]);
        setBoard(boardData);
        setTeams(teamData.teams);
        const ari = teamData.teams.find((team) => team.code === "ARI");
        setSelectedTeam(ari?.code ?? teamData.teams[0]?.code ?? "ARI");
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load prospects at this time",
        );
      }
    }
    void bootstrap();
  }, []);

  async function handleSimulate() {
    if (!selectedTeam) return;
    setLoading(true);
    setError(null);
    try {
      const result = await simulateDraft(selectedTeam, 7);
      setSimulation(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Draft simulation failed. Try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto flex max-w-5xl flex-col gap-8 px-4 py-10">
        <header className="space-y-3 rounded-2xl border border-slate-900/70 bg-slate-900/30 p-6">
          <p className="text-xs uppercase tracking-[0.4em] text-cardinalsSand">
            Draft & Scouting
          </p>
          <h1 className="text-3xl font-semibold">Prospect Board</h1>
          <p className="text-sm text-slate-300">
            Grades are placeholders derived from the manual board; future updates will sync with richer data feeds.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm text-slate-300">
              Choose team:
              <select
                className="ml-2 rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-white"
                value={selectedTeam}
                onChange={(event) => setSelectedTeam(event.target.value)}
              >
                {teams.map((team) => (
                  <option key={team.code} value={team.code}>
                    {team.display_name}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="rounded-full border border-cardinalsSand/40 bg-cardinalsRed px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-cardinalsRed/40 disabled:opacity-40"
              onClick={() => void handleSimulate()}
              disabled={loading}
            >
              {loading ? "Simulating…" : "Simulate 7-Round Draft"}
            </button>
          </div>
        </header>

        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-950/40 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        <section className="rounded-2xl border border-slate-900 bg-slate-950/60 p-6">
          <h2 className="text-xl font-semibold">Big Board</h2>
          {board ? (
            <table className="mt-4 w-full text-left text-sm text-slate-200">
              <thead className="text-xs uppercase tracking-widest text-slate-500">
                <tr>
                  <th className="px-2 py-2">Rank</th>
                  <th className="px-2 py-2">Player</th>
                  <th className="px-2 py-2">Pos</th>
                  <th className="px-2 py-2">School</th>
                  <th className="px-2 py-2">Grade</th>
                </tr>
              </thead>
              <tbody>
                {board.prospects.map((prospect, index) => (
                  <tr key={prospect.id} className="border-t border-slate-900/50">
                    <td className="px-2 py-2 text-slate-400">#{index + 1}</td>
                    <td className="px-2 py-2 font-semibold text-white">
                      {prospect.name}
                    </td>
                    <td className="px-2 py-2">{prospect.position}</td>
                    <td className="px-2 py-2 text-slate-300">{prospect.school}</td>
                    <td className="px-2 py-2 text-cardinalsSand">{prospect.grade}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-slate-400">Loading board…</p>
          )}
        </section>

        {simulation && (
          <section className="rounded-2xl border border-slate-900 bg-slate-950/60 p-6">
            <h2 className="text-xl font-semibold">Draft Results</h2>
            <p className="text-sm text-slate-300">
              Showing picks for {simulation.team} plus the full order.
            </p>
            <div className="mt-4 grid gap-6 lg:grid-cols-2">
              <div>
                <h3 className="text-sm uppercase tracking-widest text-slate-500">
                  Your Picks
                </h3>
                {simulation.team_picks.length === 0 ? (
                  <p className="text-sm text-slate-400">No selections available.</p>
                ) : (
                  <ul className="mt-3 space-y-2 text-sm text-slate-200">
                    {simulation.team_picks.map((pick) => (
                      <li
                        key={pick.overall}
                        className="rounded-lg border border-slate-900/50 bg-slate-900/40 px-3 py-2"
                      >
                        <span className="font-semibold text-white">
                          Pick #{pick.overall} (R{pick.round}) — {pick.prospect.name}
                        </span>
                        <p className="text-xs text-slate-400">
                          {pick.prospect.position} · {pick.prospect.school} (Grade {pick.prospect.grade})
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <h3 className="text-sm uppercase tracking-widest text-slate-500">
                  First 16 Picks
                </h3>
                <ul className="mt-3 space-y-2 text-sm text-slate-200">
                  {simulation.picks.slice(0, 16).map((pick) => (
                    <li
                      key={pick.overall}
                      className="rounded-lg border border-slate-900/50 bg-slate-900/40 px-3 py-2"
                    >
                      <span className="font-semibold text-white">
                        #{pick.overall} {pick.team} — {pick.prospect.name}
                      </span>
                      <p className="text-xs text-slate-400">
                        {pick.prospect.position} · {pick.prospect.school} (Grade {pick.prospect.grade})
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
