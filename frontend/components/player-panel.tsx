import { PlayerDetailResponse } from "../lib/api";

type Props = {
  detail: PlayerDetailResponse | null;
  loading: boolean;
};

export function PlayerPanel({ detail, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-6 text-sm text-slate-300">
        Loading player profile…
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-6 text-sm text-slate-400">
        Select a player to inspect their bio and contract terms.
      </div>
    );
  }

  const { player, contracts } = detail;
  const vitals = buildVitals(player);

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
      <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <div className="space-y-4">
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-widest text-slate-400">
              Player Profile
            </p>
            <h2 className="text-2xl font-semibold text-white">
              {player.full_name}
            </h2>
            <p className="text-sm text-slate-300">
              {player.position} •{" "}
              {player.jersey_number ? `#${player.jersey_number}` : "No jersey"} •{" "}
              {player.status.toLowerCase()}
            </p>
          </div>

          <dl className="grid grid-cols-2 gap-4 text-xs text-slate-400 sm:grid-cols-3">
            {vitals.map((item) => (
              <div key={item.label}>
                <dt className="uppercase tracking-wide">{item.label}</dt>
                <dd className="text-base font-semibold text-white">
                  {item.value}
                </dd>
              </div>
            ))}
          </dl>

        </div>

        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-200">
            Contract Summary
          </h3>
          {contracts.length === 0 ? (
            <p className="text-sm text-slate-400">
              No contract data in this snapshot.
            </p>
          ) : (
            <div className="space-y-3">
              {contracts.map((contract) => (
                <article
                  key={contract.id}
                  className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-sm"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 text-slate-300">
                    <span>{contract.source}</span>
                    {contract.signed_date && (
                      <span className="text-xs text-slate-500">
                        Signed {formatDate(contract.signed_date)}
                      </span>
                    )}
                  </div>
                  <dl className="mt-4 grid grid-cols-2 gap-3 text-xs text-slate-400">
                    <div>
                      <dt className="uppercase tracking-wide">Value</dt>
                      <dd className="text-base font-semibold text-white">
                        {formatCurrency(contract.total_value)}
                      </dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-wide">APY</dt>
                      <dd className="text-base font-semibold text-cardinalsSand">
                        {formatCurrency(contract.average_per_year)}
                      </dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-wide">
                        Guaranteed Cash
                      </dt>
                      <dd className="text-base font-semibold text-white">
                        {formatCurrency(contract.guaranteed)}
                      </dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-wide">Notes</dt>
                      <dd className="text-white">
                        {contract.notes?.length ? contract.notes : "—"}
                      </dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function buildVitals(player: PlayerDetailResponse["player"]) {
  const entries: { label: string; value: string }[] = [];

  entries.push({
    label: "Experience",
    value: `${player.experience} yr${player.experience === 1 ? "" : "s"}`,
  });

  entries.push({
    label: "College",
    value: player.college ?? "—",
  });

  entries.push({
    label: "Height / Weight",
    value:
      player.height && player.weight
        ? `${player.height} / ${player.weight} lbs`
        : "—",
  });

  entries.push({
    label: "Age",
    value: player.birthdate ? formatAge(player.birthdate) : "—",
  });

  entries.push({
    label: "Status",
    value: player.status.toLowerCase(),
  });

  entries.push({
    label: "Roster Date",
    value: player.roster_date ? formatDate(player.roster_date) : "—",
  });

  return entries;
}

function formatCurrency(value: number | null) {
  if (!value || Number.isNaN(value)) {
    return "—";
  }
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
    year: "numeric",
  }).format(new Date(value));
}

function formatAge(value: string) {
  const birth = new Date(value);
  if (Number.isNaN(birth.getTime())) {
    return "—";
  }
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  const m = now.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) {
    age -= 1;
  }
  return `${age}`;
}
