import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "@/api/client";
import { login, register } from "@/api/auth";
import { useAuth } from "@/lib/auth";
import { Aurora } from "@/features/branding/Aurora";
import { BrandMark } from "@/features/branding/BrandMark";

type Mode = "login" | "register";

/** Sign in / Register screen (docs/11 §1). Animated welcome + auth, then routes new
 *  users into onboarding and returning users back where they came from. */
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
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Where to return after auth (set by RequireAuth), default to the feed.
  const from = (location.state as { from?: string } | null)?.from ?? "/feed";

  const switchMode = (next: Mode) => {
    if (next === mode) return;
    setMode(next);
    setError(null);
  };

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
      // New accounts go through onboarding; returning users resume their session.
      navigate(mode === "register" ? "/onboarding" : from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong. Is the API running?");
    } finally {
      setBusy(false);
    }
  };

  const isRegister = mode === "register";

  return (
    <div className="welcome">
      <Aurora />

      <div className="welcome__inner">
        <header className="welcome__hero">
          <BrandMark size={64} />
          <h1 className="welcome__title">Forge</h1>
          <p className="welcome__tagline">Your AI coach for training, food, and progress.</p>
        </header>

        <form className="auth-card" onSubmit={onSubmit}>
          <div className="segmented" role="tablist" aria-label="Login or sign up">
            <span className={`segmented__pill segmented__pill--${mode}`} aria-hidden="true" />
            <button
              type="button"
              role="tab"
              aria-selected={!isRegister}
              className={`segmented__btn ${!isRegister ? "is-active" : ""}`}
              onClick={() => switchMode("login")}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={isRegister}
              className={`segmented__btn ${isRegister ? "is-active" : ""}`}
              onClick={() => switchMode("register")}
            >
              Create account
            </button>
          </div>

          {/* key forces the fields to replay their entrance when switching modes */}
          <div className="auth-card__fields" key={mode}>
            <label className="floaty">
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder=" "
                required
              />
              <span className="floaty__label">Email</span>
            </label>

            {isRegister && (
              <>
                <div className="floaty-row">
                  <label className="floaty">
                    <input
                      type="text"
                      autoComplete="given-name"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      placeholder=" "
                      maxLength={60}
                      required
                    />
                    <span className="floaty__label">First name</span>
                  </label>
                  <label className="floaty">
                    <input
                      type="text"
                      autoComplete="family-name"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      placeholder=" "
                      maxLength={60}
                    />
                    <span className="floaty__label">Last name</span>
                  </label>
                </div>
                <label className="floaty">
                  <input
                    type="text"
                    autoComplete="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder=" "
                    minLength={3}
                    maxLength={30}
                    pattern="[a-zA-Z0-9_]+"
                    title="3–30 chars: letters, numbers, underscore"
                    required
                  />
                  <span className="floaty__label">Username</span>
                </label>
              </>
            )}

            <label className="floaty">
              <input
                type={showPassword ? "text" : "password"}
                autoComplete={isRegister ? "new-password" : "current-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder=" "
                minLength={8}
                required
              />
              <span className="floaty__label">Password</span>
              <button
                type="button"
                className="floaty__reveal"
                onClick={() => setShowPassword((s) => !s)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </label>
          </div>

          {error && <p className="auth-card__error">{error}</p>}

          <button className={`btn-primary ${busy ? "is-busy" : ""}`} type="submit" disabled={busy}>
            <span className="btn-primary__label">
              {busy ? "Just a sec…" : isRegister ? "Create my account" : "Sign in"}
            </span>
            <span className="btn-primary__shine" aria-hidden="true" />
          </button>

          <p className="auth-card__legal">
            {isRegister
              ? "By continuing you agree to our Terms & Privacy Policy."
              : "Trouble signing in? Double-check your email and password."}
          </p>
        </form>
      </div>
    </div>
  );
}
