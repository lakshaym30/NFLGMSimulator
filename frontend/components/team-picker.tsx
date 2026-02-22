import { TeamSummary } from "../lib/api";

type Props = {
  teams: TeamSummary[];
  value: string | null;
  onChange: (teamCode: string) => void;
  disabled?: boolean;
};

export function TeamPicker({ teams, value, onChange, disabled }: Props) {
  return (
    <label className="flex w-full flex-col gap-2 text-sm font-medium text-slate-200">
      Team
      <select
        className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-base text-white focus:border-cardinalsSand focus:outline-none focus:ring-1 focus:ring-cardinalsSand disabled:opacity-50"
        value={value ?? ""}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        {!value && <option value="">Select a team</option>}
        {teams.map((team) => (
          <option key={team.code} value={team.code}>
            {team.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}
