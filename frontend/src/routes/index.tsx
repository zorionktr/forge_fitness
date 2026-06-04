import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "@/app/AppLayout";
import { ChatScreen } from "@/features/chat/ChatScreen";
import { FeedScreen } from "@/features/feed/FeedScreen";
import { NutritionScreen } from "@/features/nutrition/NutritionScreen";
import { RequireAuth } from "@/features/auth/RequireAuth";
import { SignInScreen } from "@/features/auth/SignInScreen";
import { OnboardingScreen } from "@/features/onboarding/OnboardingScreen";
import { DiscoverScreen } from "@/features/discover/DiscoverScreen";
import { ProfileScreen } from "@/features/profile/ProfileScreen";
import { PublicProfileScreen } from "@/features/profile/PublicProfileScreen";
import { ProgressScreen } from "@/features/progress/ProgressScreen";

// Feature screens are lazy-loaded in a fuller build. Scaffold wires the core routes (docs/08 §2).
export const router = createBrowserRouter([
  { path: "/sign-in", element: <SignInScreen /> },
  {
    path: "/",
    element: <RequireAuth />, // everything below requires a session (docs/11 §2)
    children: [
      // Onboarding is authed but full-screen (no tab bar / app chrome).
      { path: "onboarding", element: <OnboardingScreen /> },
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <Navigate to="/feed" replace /> },
          { path: "feed", element: <FeedScreen /> },
          { path: "discover", element: <DiscoverScreen /> },
          { path: "u/:userId", element: <PublicProfileScreen /> },
          { path: "chat", element: <ChatScreen /> },
          { path: "nutrition", element: <NutritionScreen /> },
          { path: "progress", element: <ProgressScreen /> },
          { path: "communities", element: <div className="screen">Communities (docs/06)</div> },
          { path: "profile", element: <ProfileScreen /> },
        ],
      },
    ],
  },
]);
