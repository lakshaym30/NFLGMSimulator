import { CapEntry, PlayerSummary } from "../lib/api";

type Props = {
  players: PlayerSummary[];
  capEntries: CapEntry[];
};

const OFFENSE = new Set([
  "QB",
  "RB",
  "FB",
  "WR",
  "TE",
  "LT",
  "LG",
  "C",
  "RG",
  "RT",
  "OL",
  "T",
  "G",
]);
const DEFENSE = new Set([
  "DE",
  "DT",
  "NT",
  "DL",
  "EDGE",
  "LB",
  "OLB",
  "ILB",
  "MLB",
  "CB",
  "DB",
  "S",
  "FS",
  "SS",
]);
const SPECIAL = new Set(["K", "P", "LS", "KR", "PR"]);

export function RosterInsights({ players, capEntries }: Props) {
  const totalPlayers = players.length;
  const positionCounts = aggregatePositions(players);
  const topPositions = positionCounts.slice(0, 6);
  const averageExperience = calcAverageExperience(players);
  const averageAge = calcAverageAge(players);
  const capShares = calcCapShares(players, capEntries);

  return (
    <section className="rounded-2xl border border-slate-900 bg-slate-950/60 p-5 shadow-inner shadow-black/30">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-slate-500">
            Roster Insights
          </p>
          <h2 className="text-lg font-semibold text-white">Composition Snapshot</h2>
        </div>
        <p className="text-sm text-slate-400">{totalPlayers} players</p>
      </header>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <article className="rounded-xl border border-slate-900/50 bg-slate-900/40 p-4">
          <h3 className="text-xs uppercase tracking-widest text-slate-400">
            Position mix
          </h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-200">
            {topPositions.map(([group, count]) => (
              <li key={group} className="flex items-center justify-between">
                <span className="font-semibold text-white">{group}</span>
                <span className="text-slate-300">{count}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="rounded-xl border border-slate-900/50 bg-slate-900/40 p-4 space-y-3 text-sm">
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-400">
              Avg. Experience
            </p>
            <p className="text-2xl font-semibold text-white">
              {Number.isFinite(averageExperience)
                ? `${averageExperience.toFixed(1)} yrs`
                : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-400">
              Avg. Age
            </p>
            <p className="text-2xl font-semibold text-white">
              {Number.isFinite(averageAge) ? `${averageAge.toFixed(1)} yrs` : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-400">
              Cap share
            </p>
            <ul className="mt-2 space-y-1 text-slate-300">
              {capShares.map((entry) => (
                <li key={entry.label} className="flex items-center justify-between">
                  <span>{entry.label}</span>
                  <span className="font-semibold text-white">
                    {entry.share.toFixed(1)}%
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </article>
      </div>
    </section>
  );
}

function aggregatePositions(players: PlayerSummary[]) {
  const counts: Record<string, number> = {};
  for (const player of players) {
    const key = normalizePosition(player.position);
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1]);
}

function normalizePosition(pos?: string) {
  if (!pos) {
    return "Other";
  }
  const upper = pos.toUpperCase();
  if (upper.includes("LINEBACKER")) return "LB";
  if (upper.includes("CORNER")) return "CB";
  if (upper.includes("SAFETY")) return "S";
  if (upper.includes("TACKLE")) return "T";
  if (upper.includes("GUARD")) return "G";
  if (upper.includes("CENTER")) return "C";
  if (upper.includes("END")) return "DE";
  if (upper.includes("DEFENSIVE TACKLE")) return "DT";
  if (upper.includes("DEFENSIVE LINE")) return "DL";
  return upper.replaceAll(".", "");
}

function calcAverageExperience(players: PlayerSummary[]) {
  if (!players.length) return NaN;
  const total = players.reduce((sum, player) => sum + (player.experience ?? 0), 0);
  return total / players.length;
}

function calcAverageAge(players: PlayerSummary[]) {
  const ages: number[] = [];
  for (const player of players) {
    if (!player.birthdate) continue;
    try {
      const [year, month, day] = player.birthdate.split("-").map(Number);
      if (!year || !month || !day) continue;
      const birth = new Date(Date.UTC(year, month - 1, day));
      if (Number.isNaN(birth.getTime())) continue;
      const now = new Date();
      let age = now.getUTCFullYear() - birth.getUTCFullYear();
      const monthDiff = now.getUTCMonth() - birth.getUTCMonth();
      if (monthDiff < 0 || (monthDiff === 0 && now.getUTCDate() < birth.getUTCDate())) {
        age -= 1;
      }
      ages.push(age);
    } catch (error) {
      continue;
    }
  }
  if (!ages.length) return NaN;
  return ages.reduce((sum, age) => sum + age, 0) / ages.length;
}

function ageFromDate(value: string) {
  const birth = new Date(value);
  if (Number.isNaN(birth.getTime())) {
    return NaN;
  }
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  const monthDiff = now.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && now.getDate() < birth.getDate())) {
    age -= 1;
  }
  return age;
}

function calcCapShares(players: PlayerSummary[], entries: CapEntry[]) {
  if (!entries.length) {
    return [
      { label: "Offense", share: 0 },
      { label: "Defense", share: 0 },
      { label: "Special", share: 0 },
    ];
  }

  const playerById = new Map(players.map((player) => [player.id, player]));
  let offense = 0;
  let defense = 0;
  let special = 0;
  let other = 0;

  for (const entry of entries) {
    const player = playerById.get(entry.player_id);
    if (!player) {
      other += entry.cap_hit;
      continue;
    }
    const pos = normalizePosition(player.position);
    const capHit = entry.cap_hit ?? 0;
    if (OFFENSE.has(pos)) {
      offense += capHit;
    } else if (DEFENSE.has(pos)) {
      defense += capHit;
    } else if (SPECIAL.has(pos)) {
      special += capHit;
    } else {
      other += capHit;
    }
  }

  const total = offense + defense + special + other || 1;

  return [
    { label: "Offense", share: (offense / total) * 100 },
    { label: "Defense", share: (defense / total) * 100 },
    { label: "Special/Other", share: ((special + other) / total) * 100 },
  ];
}
