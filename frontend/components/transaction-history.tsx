import { TransactionRecord } from "../lib/api";

type Props = {
  transactions: TransactionRecord[];
  loading?: boolean;
  onUndo?: (id: number) => Promise<void> | void;
};

export function TransactionHistory({ transactions, loading, onUndo }: Props) {
  return (
    <section className="rounded-2xl border border-slate-900 bg-slate-950/60 p-5">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-slate-500">
            Ledger
          </p>
          <h2 className="text-lg font-semibold text-white">Recent Transactions</h2>
        </div>
      </header>
      {loading ? (
        <p className="mt-4 text-sm text-slate-400">Loading transactions…</p>
      ) : transactions.length === 0 ? (
        <p className="mt-4 text-sm text-slate-400">
          No moves recorded yet. Commit a release/signing to populate the log.
        </p>
      ) : (
        <ul className="mt-4 space-y-3 text-sm">
          {transactions.map((tx) => (
            <li
              key={tx.id}
              className="rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3"
            >
              <div className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
                <span>{tx.type.toUpperCase()}</span>
                <span>{formatDate(tx.created_at)}</span>
              </div>
              <p className="mt-1 font-semibold text-white">
                {tx.team.display_name} — {summaryFor(tx)}
              </p>
              <p className="text-xs text-slate-400">
                Cap delta {formatCurrency(tx.cap_delta)} | Cap space after {formatCurrency(tx.cap_space_after)}
              </p>
              {tx.notes.length > 0 && (
                <ul className="mt-1 space-y-1 text-xs text-slate-500">
                  {tx.notes.slice(0, 2).map((note) => (
                    <li key={note}>• {note}</li>
                  ))}
                </ul>
              )}
              <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                <span>Status: {tx.status}</span>
                {tx.type === "release" && tx.status === "committed" && onUndo && (
                  <button
                    type="button"
                    className="rounded-full border border-slate-700 px-3 py-1 text-xs font-semibold text-white hover:border-cardinalsSand/60"
                    onClick={() => onUndo(tx.id)}
                  >
                    Undo release
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function summaryFor(tx: TransactionRecord) {
  if (tx.type === "release") {
    const id = tx.payload.player_id ?? "player";
    return `Released player #${id}`;
  }
  if (tx.type === "sign") {
    return `Signed ${tx.payload.full_name ?? "FA"}`;
  }
  if (tx.type === "trade") {
    return `Trade with ${tx.payload.partner_team_code ?? "partner"}`;
  }
  return "Transaction";
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}
