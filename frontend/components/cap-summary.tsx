import { TeamCapResponse } from "../lib/api";

type Props = {
  cap: TeamCapResponse | null;
  loading: boolean;
};

export function CapSummary({ cap, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-6 text-sm text-slate-300">
        Calculating cap table…
      </div>
    );
  }

  if (!cap) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-6 text-sm text-slate-400">
        Cap breakdown unavailable.
      </div>
    );
  }

  const topEntries = cap.entries.slice(0, 10);

  return (
    <aside className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
      <header className="flex flex-col gap-1">
        <p className="text-xs uppercase tracking-widest text-slate-400">
          Cap Snapshot
        </p>
        <h2 className="text-2xl font-semibold text-white">
          {cap.team.display_name}
        </h2>
        <p className="text-sm text-slate-400">
          {cap.player_count} contracts tracked · {cap.top51_applied ? `${cap.considered_player_count} count toward Top-51` : "All players counted"}
        </p>
      </header>

      <dl className="mt-6 space-y-4 text-sm">
        <div className="flex items-center justify-between">
          <dt className="text-slate-400">Cap Limit</dt>
          <dd className="font-semibold text-white">{formatCurrency(cap.cap_limit)}</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-slate-400">Total Cap Hit</dt>
          <dd className="font-semibold text-cardinalsSand">
            {formatCurrency(cap.total_cap_hit)}
          </dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-slate-400">Cap Space</dt>
          <dd
            className={`font-semibold ${
              cap.cap_space >= 0 ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {formatCurrency(cap.cap_space)}
          </dd>
        </div>
      </dl>

      <div className="mt-8">
        <h3 className="text-xs uppercase tracking-widest text-slate-400">
          Top Cap Hits
        </h3>
        <ul className="mt-3 space-y-2 text-sm text-slate-200">
          {topEntries.map((entry) => (
            <li
              key={entry.player_id}
              className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/40 px-3 py-2"
            >
              <div className="flex flex-col">
                <span className="font-semibold text-white">
                  {entry.player_name}
                </span>
                <span className="text-xs text-slate-400">{entry.position}</span>
              </div>
              <span className="font-semibold text-cardinalsSand">
                {formatCurrency(entry.cap_hit)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}
