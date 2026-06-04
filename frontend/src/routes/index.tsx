import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "@/app/AppLayout";
import { ChatScreen } from "@/features/chat/ChatScreen";
import { FeedScreen } from "@/features/feed/FeedScreen";
import { NutritionScreen } from "@/features/nutrition/NutritionScreen";
import { RequireAuth } from "@/features/auth/RequireAuth";
import { SignInScreen } from "@/features/auth/SignInScreen";
import { ProfileScreen } from "@/features/profile/ProfileScreen";

// Feature screens are lazy-loaded in a fuller build. Scaffold wires the core routes (docs/08 §2).
export const router = createBrowserRouter([
  { path: "/sign-in", element: <SignInScreen /> },
  {
    path: "/",
    element: <RequireAuth />, // everything below requires a session (docs/11 §2)
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <Navigate to="/feed" replace /> },
          { path: "feed", element: <FeedScreen /> },
          { path: "chat", element: <ChatScreen /> },
          { path: "nutrition", element: <NutritionScreen /> },
          { path: "progress", element: <div className="screen">Progress (docs/02 §3.4)</div> },
          { path: "communities", element: <div className="screen">Communities (docs/06)</div> },
          { path: "profile", element: <ProfileScreen /> },
        ],
      },
    ],
  },
]);
