import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  followUser,
  getUserProfile,
  unfollowUser,
  type PublicProfile,
} from "@/api/social";
import { Avatar } from "@/features/social/Avatar";
import { ProfilePosts } from "./ProfilePosts";

const GOAL_LABELS: Record<string, string> = {
  lose: "Lose fat",
  build: "Build muscle",
  fit: "Get fit",
  health: "Stay healthy",
};

const SEX_LABELS: Record<string, string> = {
  male: "Male",
  female: "Female",
  lgbtq: "LGBTQ+",
  other: "Prefer not to say",
};

/** Read-only "stalk" view of another user, opened from search/discover. */
export function PublicProfileScreen() {
  const { userId = "" } = useParams();
  const navigate = useNavigate();

  const profileQ = useQuery({
    queryKey: ["publicProfile", userId],
    queryFn: () => getUserProfile(userId),
    enabled: !!userId,
  });
  // Redirect to own editable profile if this is me.
  useEffect(() => {
    if (profileQ.data?.is_me) navigate("/profile", { replace: true });
  }, [profileQ.data?.is_me, navigate]);

  if (profileQ.isLoading) return <div className="pubprofile">Loading…</div>;
  if (profileQ.isError || !profileQ.data) {
    return (
      <div className="pubprofile">
        <button className="pubprofile__back" onClick={() => navigate(-1)}>← Back</button>
        <p className="pubprofile__empty">This account couldn't be found.</p>
      </div>
    );
  }

  const p = profileQ.data;
  const meta = [
    p.age != null ? `${p.age} yrs` : null,
    p.sex ? SEX_LABELS[p.sex] ?? p.sex : null,
  ].filter(Boolean);

  return (
    <div className="pubprofile">
      <button className="pubprofile__back" onClick={() => navigate(-1)}>← Back</button>

      <header className="pubprofile__hero">
        <Avatar user={p} size={88} />
        <div className="pubprofile__id">
          <div className="pubprofile__name">{p.display_name || p.username}</div>
          <div className="pubprofile__handle">
            @{p.username}
            {meta.length > 0 && ` · ${meta.join(" · ")}`}
          </div>
        </div>
        <FollowButton profile={p} />
      </header>

      {p.bio && <p className="pubprofile__bio">{p.bio}</p>}

      <div className="pubprofile__stats">
        <Stat n={p.post_count} label="Posts" />
        <Stat n={p.follower_count} label="Followers" />
        <Stat n={p.following_count} label="Following" />
      </div>

      {p.gym_streak != null && p.protein_streak != null ? (
        <div className="pubprofile__streaks">
          <span className="pubprofile__streak">🔥 {p.gym_streak} gym</span>
          <span className="pubprofile__streak">🍗 {p.protein_streak} protein</span>
        </div>
      ) : (
        !p.streaks_public && <p className="pubprofile__streakHidden">Streaks hidden</p>
      )}

      {p.goals.length > 0 && (
        <div className="pubprofile__goals">
          {p.goals.map((g) => (
            <span className="pubprofile__goal" key={g}>{GOAL_LABELS[g] ?? g}</span>
          ))}
        </div>
      )}

      <section className="pubprofile__posts">
        <ProfilePosts userId={p.id} emptyText={`@${p.username} hasn't posted yet.`} />
      </section>
    </div>
  );
}

function Stat({ n, label }: { n: number; label: string }) {
  return (
    <div className="pubprofile__stat">
      <b>{n}</b>
      <span>{label}</span>
    </div>
  );
}

function FollowButton({ profile }: { profile: PublicProfile }) {
  const [following, setFollowing] = useState(profile.is_following);
  const [busy, setBusy] = useState(false);

  const toggle = async () => {
    if (busy) return;
    setBusy(true);
    const next = !following;
    setFollowing(next);
    try {
      const res = next ? await followUser(profile.id) : await unfollowUser(profile.id);
      setFollowing(res.following);
    } catch {
      setFollowing(!next);
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      className={`urow__btn ${following ? "urow__btn--on" : ""}`}
      onClick={toggle}
      disabled={busy}
    >
      {following ? "Following" : "Follow"}
    </button>
  );
}
