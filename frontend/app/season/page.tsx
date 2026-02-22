"use client";

import { useEffect, useState } from "react";
import { SeasonSimulation, TeamSummary, fetchTeams, simulateSeason } from "../../lib/api";

export default function SeasonPage() {
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string>("ARI");
  const [simulation, setSimulation] = useState<SeasonSimulation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadTeams() {
      try {
        const payload = await fetchTeams();
        setTeams(payload.teams);
        const preferred = payload.teams.find((team) => team.code === "ARI");
        setSelectedTeam(preferred?.code ?? payload.teams[0]?.code ?? "ARI");
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Unable to load teams right now",
        );
      }
    }
    void loadTeams();
  }, []);

  async function handleSimulate() {
    if (!selectedTeam) return;
    setLoading(true);
    setError(null);
    try {
      const result = await simulateSeason(selectedTeam, 17);
      setSimulation(result);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Season sim failed. Try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto flex max-w-5xl flex-col gap-8 px-4 py-10">
        <header className="space-y-3 rounded-2xl border border-slate-900/70 bg-slate-900/30 p-6">
          <h1 className="text-3xl font-semibold">Season Simulator</h1>
          <p className="text-sm text-slate-300">
            Generates a lightweight schedule and standings for experimentation. Future iterations will plug into detailed game models.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm text-slate-300">
              Team:
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
              {loading ? "Simulating…" : "Simulate Season"}
            </button>
          </div>
        </header>

        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-950/40 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        {simulation && (
          <section className="space-y-6 rounded-2xl border border-slate-900 bg-slate-950/60 p-6">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-2xl font-semibold">{simulation.team} Standings</h2>
                <p className="text-sm text-slate-300">
                  Record: {simulation.standings.wins}-{simulation.standings.losses}-{simulation.standings.ties}
                </p>
              </div>
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <div>
                <h3 className="text-sm uppercase tracking-widest text-slate-500">
                  Schedule
                </h3>
                <ul className="mt-3 space-y-2 text-sm text-slate-200">
                  {simulation.schedule.map((game) => (
                    <li
                      key={game.week}
                      className="rounded-lg border border-slate-900/50 bg-slate-900/40 px-3 py-2"
                    >
                      <span className="font-semibold text-white">
                        Week {game.week}: {game.home ? "vs" : "@"} {game.opponent}
                      </span>
                      <p className="text-xs text-slate-400">
                        {game.team_score}-{game.opponent_score} ({game.result})
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="text-sm uppercase tracking-widest text-slate-500">
                  Divisions
                </h3>
                <div className="mt-3 grid gap-4 lg:grid-cols-2">
                  {Object.entries(simulation.conference).map(([division, clubs]) => (
                    <div
                      key={division}
                      className="rounded-lg border border-slate-900/50 bg-slate-900/40 p-3"
                    >
                      <p className="text-xs uppercase tracking-widest text-slate-500">
                        {division}
                      </p>
                      <table className="mt-2 w-full text-left text-xs text-slate-200">
                        <tbody>
                          {clubs.map((club) => (
                            <tr key={club.team} className="border-t border-slate-900/60">
                              <td className="px-1 py-1 text-white">{club.team}</td>
                              <td className="px-1 py-1">{club.wins}</td>
                              <td className="px-1 py-1">{club.losses}</td>
                              <td className="px-1 py-1">{club.ties}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>
        )}

        {!simulation && !error && (
          <p className="rounded-xl border border-slate-900/60 bg-slate-900/30 p-4 text-sm text-slate-300">
            Run the simulator to generate a schedule and standings snapshot for your team.
          </p>
        )}
      </div>
    </main>
  );
}
