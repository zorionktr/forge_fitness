import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "@/api/client";
import { login, register } from "@/api/auth";
import { useAuth } from "@/lib/auth";

type Mode = "login" | "register";

/** Sign in / Register screen (docs/11 §1). Calls /auth/* and stores the session. */
export function SignInScreen() {
  const navigate = useNavigate();
  const location = useLocation();
  const setSession = useAuth((s) => s.setSession);

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Where to return after auth (set by RequireAuth), default to the feed.
  const from = (location.state as { from?: string } | null)?.from ?? "/feed";

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res =
        mode === "login"
          ? await login(email, password)
          : await register(email, username, password, firstName, lastName);
      setSession({ accessToken: res.access_token, refreshToken: res.refresh_token });
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong. Is the API running?");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth">
      <form className="auth__card" onSubmit={onSubmit}>
        <h1 className="auth__brand">Forge</h1>
        <p className="auth__subtitle">
          {mode === "login" ? "Sign in to your coach" : "Create your account"}
        </p>

        <label className="auth__field">
          <span>Email</span>
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>

        {mode === "register" && (
          <>
            <div className="auth__row">
              <label className="auth__field">
                <span>First name</span>
                <input
                  type="text"
                  autoComplete="given-name"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  maxLength={60}
                  required
                />
              </label>
              <label className="auth__field">
                <span>Last name</span>
                <input
                  type="text"
                  autoComplete="family-name"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  maxLength={60}
                />
              </label>
            </div>
            <label className="auth__field">
              <span>Username</span>
              <input
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                minLength={3}
                maxLength={30}
                pattern="[a-zA-Z0-9_]+"
                title="3–30 chars: letters, numbers, underscore"
                required
              />
            </label>
          </>
        )}

        <label className="auth__field">
          <span>Password</span>
          <input
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </label>

        {error && <p className="auth__error">{error}</p>}

        <button className="auth__submit" type="submit" disabled={busy}>
          {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
        </button>

        <button
          type="button"
          className="auth__toggle"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError(null);
          }}
        >
          {mode === "login" ? "Need an account? Register" : "Have an account? Sign in"}
        </button>
      </form>
    </div>
  );
}
