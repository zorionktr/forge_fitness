import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";

/** Gate for authenticated routes: bounces to /sign-in, remembering where you came from. */
export function RequireAuth() {
  const accessToken = useAuth((s) => s.accessToken);
  const location = useLocation();

  if (!accessToken) {
    return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}
