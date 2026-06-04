import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { queryClient } from "@/lib/query";
import { router } from "@/routes";
import "@/styles/global.css";
import "@/styles/branding.css";
import "@/styles/auth.css";
import "@/styles/onboarding.css";
import "@/styles/feed.css";
import "@/styles/social.css";
import "@/styles/progress.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
);
