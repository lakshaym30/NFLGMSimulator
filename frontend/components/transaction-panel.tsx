"use client";

import { useState } from "react";
import {
  PlayerSummary,
  TransactionPreview,
  TransactionRecord,
  previewTransaction,
  commitTransaction,
} from "../lib/api";

type Props = {
  teamCode: string | null;
  player: PlayerSummary | null;
  onCommitted: () => Promise<void> | void;
};

export function TransactionPanel({ teamCode, player, onCommitted }: Props) {
  const [preview, setPreview] = useState<TransactionPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<TransactionRecord | null>(null);

  const disabled = !teamCode || !player;

  async function handlePreviewRelease() {
    if (!teamCode || !player) return;
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await previewTransaction({
        team_code: teamCode,
        type: "release",
        payload: { player_id: player.id, post_june_1: false },
      });
      setPreview(result);
    } catch (err) {
      setPreview(null);
      setError(err instanceof Error ? err.message : "Failed to preview release");
    } finally {
      setLoading(false);
    }
  }

  async function handleCommitRelease() {
    if (!teamCode || !player) return;
    setCommitting(true);
    setError(null);
    try {
      const record = await commitTransaction({
        team_code: teamCode,
        type: "release",
        payload: { player_id: player.id, post_june_1: false },
      });
      setSuccess(record);
      setPreview(null);
      await onCommitted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to commit release");
    } finally {
      setCommitting(false);
    }
  }

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-950/60 p-5 shadow-inner shadow-black/20">
      <div className="flex flex-col gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-500">
            Transactions
          </p>
          <h2 className="text-xl font-semibold text-white">Release Player</h2>
          <p className="text-sm text-slate-400">
            Preview cap savings and dead money before cutting a player.
          </p>
        </div>

        <div className="rounded-lg border border-slate-900 bg-slate-900/50 p-4 text-sm text-slate-300">
          <p className="text-xs uppercase tracking-widest text-slate-500">Team</p>
          <p className="text-white">{teamCode ?? "Select a team"}</p>
          <p className="mt-2 text-xs uppercase tracking-widest text-slate-500">
            Player
          </p>
          <p className="text-white">{player?.full_name ?? "Select a player"}</p>
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/50 bg-red-950/40 p-3 text-sm text-red-200">
            {error}
          </div>
        )}

        {preview && (
          <div className="rounded-lg border border-slate-900 bg-slate-950/30 p-4 text-sm">
            <p className="text-xs uppercase tracking-widest text-slate-400">
              Preview Result
            </p>
            <dl className="mt-3 grid grid-cols-2 gap-4 text-white">
              <div>
                <dt className="text-xs text-slate-400">Cap Savings</dt>
                <dd className="text-lg font-semibold text-cardinalsSand">
                  {formatCurrency(preview.cap_delta)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-400">Dead Money</dt>
                <dd className="text-lg font-semibold">
                  {formatCurrency(preview.dead_money)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-400">Cap Space After</dt>
                <dd className="text-lg font-semibold">
                  {formatCurrency(preview.cap_space_after)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-400">Allowed</dt>
                <dd className={`text-lg font-semibold ${preview.allowed ? "text-emerald-400" : "text-red-400"}`}>
                  {preview.allowed ? "Yes" : "No"}
                </dd>
              </div>
            </dl>
            <ul className="mt-3 space-y-1 text-xs text-slate-400">
              {preview.notes.map((note) => (
                <li key={note}>• {note}</li>
              ))}
            </ul>
          </div>
        )}

        {success && (
          <div className="rounded-lg border border-emerald-500/40 bg-emerald-950/30 p-3 text-sm text-emerald-200">
            Released {success.payload.player_id} — cap delta {formatCurrency(success.cap_delta)}
          </div>
        )}

        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={handlePreviewRelease}
            disabled={disabled || loading}
            className="flex-1 rounded-md border border-slate-600 bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? "Previewing…" : "Preview Release"}
          </button>
          <button
            type="button"
            onClick={handleCommitRelease}
            disabled={disabled || committing || !player}
            className="flex-1 rounded-md border border-cardinalsSand/40 bg-cardinalsRed px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-cardinalsRed/40 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {committing ? "Committing…" : "Commit Release"}
          </button>
        </div>
      </div>
    </section>
  );
}

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "—";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}
