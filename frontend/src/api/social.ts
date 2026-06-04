import { api } from "@/api/client";

export interface Author {
  id: string;
  username: string;
  display_name: string | null;
  avatar_url: string | null;
}

export interface Post {
  id: string;
  author: Author;
  kind: string;
  body: string | null;
  media: unknown[];
  like_count: number;
  comment_count: number;
  liked_by_me: boolean;
  created_at: string;
}

export interface Comment {
  id: string;
  author: Author;
  body: string;
  created_at: string;
}

export const getFeed = () => api<Post[]>("/social/feed");

export const createPost = (body: string) =>
  api<Post>("/social/posts", { method: "POST", body: JSON.stringify({ body }) });

export const toggleLike = (postId: string) =>
  api<{ liked: boolean; like_count: number }>(`/social/posts/${postId}/like`, { method: "POST" });

export const getComments = (postId: string) => api<Comment[]>(`/social/posts/${postId}/comments`);

export const addComment = (postId: string, body: string) =>
  api<Comment>(`/social/posts/${postId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
