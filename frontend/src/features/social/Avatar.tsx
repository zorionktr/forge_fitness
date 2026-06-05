import { mediaUrl } from "@/lib/media";

interface AvatarUser {
  username: string;
  display_name: string | null;
  avatar_url: string | null;
}

/** Round user avatar: photo if present, else gradient initials. Used in discover + stories. */
export function Avatar({ user, size = 44, ring }: { user: AvatarUser; size?: number; ring?: "unseen" | "seen" | "add" }) {
  const name = user.display_name || user.username;
  const initials = name.slice(0, 2).toUpperCase();
  const cls = ring ? `uavatar uavatar--${ring}` : "uavatar";
  return (
    <span className={cls} style={{ width: size, height: size }}>
      <span className="uavatar__inner" style={{ fontSize: size * 0.36 }}>
        {user.avatar_url ? <img src={mediaUrl(user.avatar_url)} alt="" /> : initials}
      </span>
    </span>
  );
}
