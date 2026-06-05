import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "@/api/client";
import { forgotPassword, resetPassword } from "@/api/auth";
import { useAuth } from "@/lib/auth";
import { Aurora } from "@/features/branding/Aurora";
import { BrandMark } from "@/features/branding/BrandMark";

type Step = "request" | "reset";

/** Forgot / reset password (docs/11 §1). Step 1 emails a 6-digit OTP; step 2 verifies it
 *  and sets a new password, then signs the user straight in. */
export function ForgotPasswordScreen() {
  const navigate = useNavigate();
  const setSession = useAuth((s) => s.setSession);

  const [step, setStep] = useState<Step>("request");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const requestCode = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await forgotPassword(email);
      setNotice(res.message);
      setStep("reset");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong. Is the API running?");
    } finally {
      setBusy(false);
    }
  };

  const submitReset = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await resetPassword(email, otp.trim(), password);
      setSession({ accessToken: res.access_token, refreshToken: res.refresh_token });
      navigate("/feed", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong. Is the API running?");
    } finally {
      setBusy(false);
    }
  };

  const isRequest = step === "request";

  return (
    <div className="welcome">
      <Aurora />

      <div className="welcome__inner">
        <header className="welcome__hero">
          <BrandMark size={64} />
          <h1 className="welcome__title">Forge</h1>
          <p className="welcome__tagline">
            {isRequest ? "Reset your password." : "Check your email for the code."}
          </p>
        </header>

        <form className="auth-card" onSubmit={isRequest ? requestCode : submitReset}>
          {notice && <p className="auth-card__legal">{notice}</p>}

          <div className="auth-card__fields" key={step}>
            <label className="floaty">
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder=" "
                readOnly={!isRequest}
                required
              />
              <span className="floaty__label">Email</span>
            </label>

            {!isRequest && (
              <>
                <label className="floaty">
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                    placeholder=" "
                    maxLength={6}
                    minLength={6}
                    pattern="\d{6}"
                    title="6-digit code from your email"
                    required
                  />
                  <span className="floaty__label">6-digit code</span>
                </label>

                <label className="floaty">
                  <input
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder=" "
                    minLength={8}
                    required
                  />
                  <span className="floaty__label">New password</span>
                  <button
                    type="button"
                    className="floaty__reveal"
                    onClick={() => setShowPassword((s) => !s)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </label>
              </>
            )}
          </div>

          {error && <p className="auth-card__error">{error}</p>}

          <button className={`btn-primary ${busy ? "is-busy" : ""}`} type="submit" disabled={busy}>
            <span className="btn-primary__label">
              {busy ? "Just a sec…" : isRequest ? "Send reset code" : "Reset password"}
            </span>
            <span className="btn-primary__shine" aria-hidden="true" />
          </button>

          <p className="auth-card__legal">
            {!isRequest && (
              <button
                type="button"
                className="linklike"
                onClick={() => {
                  setStep("request");
                  setNotice(null);
                  setError(null);
                }}
              >
                Use a different email
              </button>
            )}
            {!isRequest && " · "}
            <Link to="/sign-in">Back to sign in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
