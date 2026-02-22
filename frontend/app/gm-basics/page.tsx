import Link from "next/link";

export const metadata = {
  title: "NFL GM Basics",
  description:
    "Primer on salary cap, roster limits, and contract mechanics used in the simulator.",
};

const sections = [
  {
    title: "League Calendar & Rosters",
    body: (
      <>
        <p>
          The league year starts every March. Teams can carry a 90-player roster in
          the offseason, but must trim to 53 players before Week 1 (plus practice-squad and
          injury-list designations). Every transaction you make in the sim immediately counts
          toward that limit, so releasing/signing players requires watching the roster delta.
        </p>
        <p>
          Negative cap balances roll forward, so you cannot simply “reset” debt at the next league year.
        </p>
      </>
    ),
  },
  {
    title: "Salary Cap Fundamentals",
    body: (
      <>
        <p>
          The NFL uses a hard cap (\$255.4M for the current league year). There is no luxury tax —
          if a move pushes your franchise over the limit, it is invalid unless you free space elsewhere.
        </p>
        <p>
          In reality only the top 51 cap hits count during the offseason; to keep the math transparent,
          the current simulator counts every player. Once per-player contract data is richer the app
          will flip to the Top-51 rule automatically.
        </p>
      </>
    ),
  },
  {
    title: "Contract Components",
    body: (
      <>
        <ul className="list-disc space-y-1 pl-6 text-slate-200">
          <li>
            <strong>Base salary</strong>: annual cash paid when the player is on the roster. Counts in full that year.
          </li>
          <li>
            <strong>Signing bonus</strong>: paid upfront but prorated over up to five years (including voids). Cutting a
            player accelerates the remaining proration into dead money.
          </li>
          <li>
            <strong>Roster/workout bonuses</strong>: trigger on specific dates. Helpful for cap games by moving cash
            between seasons.
          </li>
          <li>
            <strong>Guaranteed cash</strong>: money owed even if the player is released. This is the key driver for dead
            money in the sim.
          </li>
        </ul>
        <p className="mt-3">
          The current data pipeline only carries total value, APY, and total guaranteed. That’s enough for rough cap
          previews, but we are missing signing bonus amounts and per-year breakdowns. Future iterations will pull the full
          Spotrac/OTC contract rows (signing bonus, base salary per season, bonuses, void-year flags) so release math
          matches reality.
        </p>
      </>
    ),
  },
  {
    title: "Transactions Supported Today",
    body: (
      <>
        <p>
          The current build includes preview + commit flows for releases, signings, and trades. Releases approximate dead money
          by treating guaranteed cash as the penalty, trades move future base salaries to the acquiring team, and signings
          simply insert a new contract. Every move logs an audit row so you can replay cap history.
        </p>
        <p>
          Releasing a player after June 1 splits dead money between the current and following league years; the UI shows
          both values in the preview panel.
        </p>
      </>
    ),
  },
  {
    title: "What’s Next",
    body: (
      <>
        <p>
          Upcoming enhancements include restructures, extensions, draft-pick handling, Top-51 accounting, and richer
          contract ingestion. Each feature will extend this page so non-technical players know how the rules work and
          which approximations the sim still makes.
        </p>
      </>
    ),
  },
];

export default function GMBasicsPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-4xl px-4 py-12 space-y-10">
        <header className="space-y-4">
          <p className="text-xs uppercase tracking-[0.35em] text-cardinalsSand">
            Learn the Job
          </p>
          <h1 className="text-4xl font-semibold">NFL GM Basics</h1>
          <p className="text-base text-slate-300">
            Salary cap rules, roster limits, and contract mechanics summarized so you can build a realistic franchise.
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-full border border-cardinalsSand/40 bg-cardinalsRed px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-cardinalsRed/40"
          >
            ← Back to dashboard
          </Link>
        </header>

        <div className="space-y-8">
          {sections.map((section) => (
            <article
              key={section.title}
              className="rounded-2xl border border-slate-900 bg-slate-950/60 p-6 shadow-inner shadow-black/20"
            >
              <h2 className="text-2xl font-semibold text-white">{section.title}</h2>
              <div className="mt-4 space-y-3 text-sm text-slate-200">{section.body}</div>
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}
