import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getLeaderboard,
  getMyStreaks,
  gymCheckin,
  undoGymCheckin,
  type LeaderboardEntry,
} from "@/api/streaks";
import { Avatar } from "@/features/social/Avatar";

/** Streaks + friends leaderboard. The "Progress" tab. */
export function ProgressScreen() {
  const qc = useQueryClient();

  const streaksQ = useQuery({ queryKey: ["myStreaks"], queryFn: getMyStreaks });
  const boardQ = useQuery({ queryKey: ["leaderboard"], queryFn: getLeaderboard });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["myStreaks"] });
    qc.invalidateQueries({ queryKey: ["leaderboard"] });
  };

  const checkin = useMutation({ mutationFn: gymCheckin, onSuccess: refresh });
  const uncheck = useMutation({ mutationFn: undoGymCheckin, onSuccess: refresh });

  const s = streaksQ.data;
  const busy = checkin.isPending || uncheck.isPending;
  const checkedIn = s?.today.gym_checked_in ?? false;

  const proteinPct =
    s && s.today.protein_target_g
      ? Math.min(100, Math.round((s.today.protein_logged_g / s.today.protein_target_g) * 100))
      : 0;

  return (
    <div className="prog">
      <h1 className="prog__h1">Your streaks</h1>

      <div className="prog__streaks">
        <StreakCard emoji="🔥" label="Gym streak" value={s?.gym_streak ?? 0} on={checkedIn} />
        <StreakCard emoji="🍗" label="Protein streak" value={s?.protein_streak ?? 0} on={s?.today.protein_met ?? false} />
      </div>

      <section className="prog__today">
        <div className="prog__todayRow">
          <div className="prog__todayText">
            <b>Hit the gym today?</b>
            <span>{checkedIn ? "Checked in — nice work." : "One tap keeps your streak alive."}</span>
          </div>
          <button
            className={`prog__check ${checkedIn ? "prog__check--on" : ""}`}
            disabled={busy}
            onClick={() => (checkedIn ? uncheck.mutate() : checkin.mutate())}
          >
            {checkedIn ? "✓ Trained" : "Check in"}
          </button>
        </div>

        <div className="prog__todayRow prog__todayRow--col">
          <div className="prog__proteinHead">
            <b>Protein today</b>
            {s?.today.protein_target_g != null ? (
              <span>
                {Math.round(s.today.protein_logged_g)} / {Math.round(s.today.protein_target_g)} g
              </span>
            ) : (
              <span>Add your weight to set a target</span>
            )}
          </div>
          {s?.today.protein_target_g != null && (
            <div className="prog__bar">
              <span
                className={`prog__barFill ${s.today.protein_met ? "is-done" : ""}`}
                style={{ width: `${proteinPct}%` }}
              />
            </div>
          )}
          {s?.today.protein_target_g == null && (
            <Link className="prog__link" to="/profile">Update profile →</Link>
          )}
        </div>
      </section>

      <h2 className="prog__h2">
        Leaderboard
        {boardQ.data && <span className="prog__sub"> · last {boardQ.data.window_days} days</span>}
      </h2>

      <section className="prog__board">
        {boardQ.isLoading && <p className="prog__empty">Loading…</p>}
        {boardQ.data && boardQ.data.entries.length <= 1 && (
          <p className="prog__empty">
            Follow friends from <Link className="prog__link" to="/discover">Discover</Link> to race them here.
          </p>
        )}
        {boardQ.data?.entries.map((e, i) => (
          <BoardRow key={e.user.id} entry={e} rank={i + 1} />
        ))}
      </section>
    </div>
  );
}

function StreakCard({ emoji, label, value, on }: { emoji: string; label: string; value: number; on: boolean }) {
  return (
    <div className={`prog__card ${on ? "prog__card--on" : ""}`}>
      <span className="prog__cardEmoji">{emoji}</span>
      <span className="prog__cardNum">{value}</span>
      <span className="prog__cardLabel">{label}</span>
    </div>
  );
}

function BoardRow({ entry, rank }: { entry: LeaderboardEntry; rank: number }) {
  const medal = rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : `${rank}`;
  return (
    <div className={`prog__row ${entry.is_me ? "prog__row--me" : ""}`}>
      <span className="prog__rank">{medal}</span>
      <Link className="prog__rowUser" to={entry.is_me ? "/profile" : `/u/${entry.user.id}`}>
        <Avatar user={entry.user} size={38} />
        <span className="prog__rowName">
          {entry.user.display_name || entry.user.username}
          {entry.is_me && <em> (you)</em>}
        </span>
      </Link>
      <span className="prog__rowStats">
        <span title="Gym days">🔥 {entry.gym_days}</span>
        <span title="Protein days">🍗 {entry.protein_days}</span>
      </span>
    </div>
  );
}
