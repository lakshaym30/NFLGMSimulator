import { PlayerSummary } from "../lib/api";

export type SortKey =
  | "name"
  | "position"
  | "jersey"
  | "status"
  | "experience"
  | "capHit";
export type SortDirection = "asc" | "desc";

type Props = {
  players: PlayerSummary[];
  selectedPlayerId: number | null;
  loading: boolean;
  onSelect: (playerId: number) => void;
  sortKey: SortKey;
  sortDirection: SortDirection;
  onSortChange: (key: SortKey) => void;
};

export function RosterTable({
  players,
  selectedPlayerId,
  loading,
  onSelect,
  sortKey,
  sortDirection,
  onSortChange,
}: Props) {
  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-6 text-sm text-slate-300">
        Loading roster…
      </div>
    );
  }

  if (!players.length) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-6 text-sm text-slate-300">
        No players found for this roster snapshot.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/70">
      <div className="overflow-x-auto">
      <table className="min-w-full border-collapse text-left text-xs text-slate-200 sm:text-sm">
        <thead className="bg-slate-900 text-xs uppercase tracking-wider text-slate-400">
          <tr>
            <SortableHeader
              label="Player"
              column="name"
              sortKey={sortKey}
              sortDirection={sortDirection}
              onClick={onSortChange}
            />
            <SortableHeader
              label="Pos"
              column="position"
              sortKey={sortKey}
              sortDirection={sortDirection}
              onClick={onSortChange}
            />
            <SortableHeader
              label="#"
              column="jersey"
              sortKey={sortKey}
              sortDirection={sortDirection}
              onClick={onSortChange}
            />
            <SortableHeader
              label="Status"
              column="status"
              sortKey={sortKey}
              sortDirection={sortDirection}
              onClick={onSortChange}
            />
            <SortableHeader
              label="Exp"
              column="experience"
              align="right"
              sortKey={sortKey}
              sortDirection={sortDirection}
              onClick={onSortChange}
            />
            <SortableHeader
              label="Cap Hit"
              column="capHit"
              align="right"
              sortKey={sortKey}
              sortDirection={sortDirection}
              onClick={onSortChange}
            />
          </tr>
        </thead>
        <tbody>
          {players.map((player) => {
            const isSelected = player.id === selectedPlayerId;
            return (
              <tr
                key={player.id}
                className={`cursor-pointer border-t border-slate-900/70 transition hover:bg-slate-900 ${
                  isSelected ? "bg-slate-900" : ""
                }`}
                onClick={() => onSelect(player.id)}
              >
                <td className="px-4 py-3 font-semibold text-white">
                  {player.full_name}
                  {player.college && (
                    <span className="block text-xs font-normal text-slate-400">
                      {player.college}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 font-mono text-sm text-slate-300">
                  {player.position}
                </td>
                <td className="px-4 py-3">{player.jersey_number ?? "—"}</td>
                <td className="px-4 py-3 capitalize text-slate-300">
                  {player.status.toLowerCase()}
                </td>
                <td className="px-4 py-3 text-right font-semibold text-white">
                  {player.experience}
                </td>
                <td className="px-4 py-3 text-right text-cardinalsSand">
                  {formatCurrency(player.contract?.average_per_year)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    </div>
  );
}

function formatCurrency(value: number | null | undefined) {
  if (!value || Number.isNaN(value)) {
    return "—";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

type SortableHeaderProps = {
  label: string;
  column: SortKey;
  sortKey: SortKey;
  sortDirection: SortDirection;
  onClick: (key: SortKey) => void;
  align?: "left" | "right";
};

function SortableHeader({
  label,
  column,
  sortKey,
  sortDirection,
  onClick,
  align = "left",
}: SortableHeaderProps) {
  const isActive = sortKey === column;
  return (
    <th className={`px-4 py-3 ${align === "right" ? "text-right" : ""}`}>
      <button
        type="button"
        className={`flex items-center gap-1 text-xs font-semibold uppercase tracking-widest text-slate-400 ${
          align === "right" ? "justify-end" : "justify-start"
        }`}
        onClick={() => onClick(column)}
      >
        {label}
        {isActive && (
          <span className="text-slate-300">
            {sortDirection === "asc" ? "↑" : "↓"}
          </span>
        )}
      </button>
    </th>
  );
}
