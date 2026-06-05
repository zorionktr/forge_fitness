import { api, apiUpload } from "@/api/client";

export interface Author {
  id: string;
  username: string;
  display_name: string | null;
  avatar_url: string | null;
}

export interface Media {
  url: string;
  type: string; // "image"
  w?: number;
  h?: number;
}

export interface Post {
  id: string;
  author: Author;
  kind: string;
  body: string | null;
  media: Media[];
  tags: string[];
  like_count: number;
  comment_count: number;
  liked_by_me: boolean;
  created_at: string;
  reason?: string | null;
}

export interface Comment {
  id: string;
  author: Author;
  body: string;
  created_at: string;
}

export interface UserCard {
  id: string;
  username: string;
  display_name: string | null;
  avatar_url: string | null;
  follower_count: number;
  is_following: boolean;
}

export interface StoryItem {
  id: string;
  author: Author;
  media: Media[];
  caption: string | null;
  created_at: string;
  expires_at: string;
  like_count: number;
  comment_count: number;
  liked_by_me: boolean;
}

export interface StoryTray {
  author: Author;
  items: StoryItem[];
}

export const getFeed = (limit = 10, offset = 0) =>
  api<Post[]>(`/social/feed?limit=${limit}&offset=${offset}`);

export interface NewPost {
  body?: string;
  tags?: string[];
  media?: Media[];
  kind?: string; // "text" (default) | "pr" | ...
}

export const createPost = (post: NewPost) =>
  api<Post>("/social/posts", { method: "POST", body: JSON.stringify(post) });

/** Upload post images (camera/gallery) and get back media descriptors to attach to a post. */
export function uploadPostMedia(files: File[]): Promise<Media[]> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  return apiUpload<Media[]>("/social/media", form);
}

export const toggleLike = (postId: string) =>
  api<{ liked: boolean; like_count: number }>(`/social/posts/${postId}/like`, { method: "POST" });

export const getComments = (postId: string) => api<Comment[]>(`/social/posts/${postId}/comments`);

export const addComment = (postId: string, body: string) =>
  api<Comment>(`/social/posts/${postId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });

// ---- Social graph: follows + discover ----

export interface FollowState {
  following: boolean;
  follower_count: number;
}

export const followUser = (userId: string) =>
  api<FollowState>(`/social/users/${userId}/follow`, { method: "POST" });

export const unfollowUser = (userId: string) =>
  api<FollowState>(`/social/users/${userId}/follow`, { method: "DELETE" });

export const searchUsers = (q: string) =>
  api<UserCard[]>(`/social/users/search?q=${encodeURIComponent(q)}`);

export const getSuggestedUsers = () => api<UserCard[]>("/social/users/suggested");

export interface PublicProfile {
  id: string;
  username: string;
  display_name: string | null;
  avatar_url: string | null;
  bio: string | null;
  age: number | null;
  sex: string | null;
  goals: string[];
  follower_count: number;
  following_count: number;
  post_count: number;
  is_following: boolean;
  is_me: boolean;
  streaks_public: boolean;
  gym_streak: number | null;
  protein_streak: number | null;
}

export const getUserProfile = (userId: string) =>
  api<PublicProfile>(`/social/users/${userId}`);

export const getUserPosts = (userId: string, limit = 10, offset = 0) =>
  api<Post[]>(`/social/users/${userId}/posts?limit=${limit}&offset=${offset}`);

// ---- Stories ----

export const getStories = () => api<StoryTray[]>("/social/stories");

export const createStory = (media: Media[], caption?: string) =>
  api<StoryItem>("/social/stories", {
    method: "POST",
    body: JSON.stringify({ media, caption: caption || null }),
  });

export const likeStory = (storyId: string) =>
  api<{ liked: boolean; like_count: number }>(`/social/stories/${storyId}/like`, { method: "POST" });

export const getStoryComments = (storyId: string) =>
  api<Comment[]>(`/social/stories/${storyId}/comments`);

export const addStoryComment = (storyId: string, body: string) =>
  api<Comment>(`/social/stories/${storyId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
