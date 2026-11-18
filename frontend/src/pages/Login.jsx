import { useEffect, useRef, useState } from "react";
import {
  loginUser,
  registerUser,
  resendVerificationEmail,
  verifyEmail,
} from "../services/api";


export default function Login({ onLogin }) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pendingEmail, setPendingEmail] = useState("");
  const verificationHandled = useRef(false);

  useEffect(() => {
    if (verificationHandled.current) return;

    const currentUrl = new URL(window.location.href);
    const verificationToken = currentUrl.searchParams.get("verify_email");

    if (!verificationToken) return;

    verificationHandled.current = true;

    // Remove the one-time token from the visible URL and browser history.
    window.history.replaceState(
      {},
      document.title,
      `${currentUrl.pathname}${currentUrl.hash}`
    );

    setIsRegistering(false);
    setError("");
    setMessage("Verifying your email address...");

    verifyEmail(verificationToken)
      .then((result) => {
        setMessage(result.message || "Email verified. You can now log in.");
        setError("");
      })
      .catch((err) => {
        setMessage("");
        setError(err.message);
      });
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      if (isRegistering) {
        const result = await registerUser(email, password);
        setPendingEmail(email.trim());
        setIsRegistering(false);
        setMessage(result.message || "Check your inbox for the verification link.");
        return;
      }

      const result = await loginUser(email, password);

      localStorage.setItem(
        "founderverse_token",
        result.access_token
      );
      localStorage.setItem(
        "founderverse_user_id",
        result.user_id
      );

      if (result.company_id) {
        localStorage.setItem(
          "founderverse_company_id",
          result.company_id
        );
      }

      onLogin(result);
    } catch (err) {
      setError(err.message);
      if (err.code === "EMAIL_NOT_VERIFIED") {
        setPendingEmail(email.trim());
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleResendVerification() {
    if (!pendingEmail) return;

    setError("");
    setMessage("");
    setResendLoading(true);

    try {
      const result = await resendVerificationEmail(pendingEmail);
      setMessage(result.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setResendLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="brand-logo">F</div>
          <div>
            <h1>FounderVerse</h1>
            <p>AI Startup Simulator</p>
          </div>
        </div>

        <div className="auth-heading">
          <span>YOUR STARTUP JOURNEY</span>
          <h2>
            {isRegistering
              ? "Create your founder account."
              : "Welcome back, Founder."}
          </h2>
          <p>
            {isRegistering
              ? "Create your account. We'll email you a link to verify your address."
              : "Continue your startup journey."}
          </p>
        </div>

        {message && (
          <div className="auth-success" role="status">
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <label>Email</label>
          <input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />

          <label>Password</label>
          <input
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoComplete={isRegistering ? "new-password" : "current-password"}
          />

          {error && (
            <div className="auth-error" role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="primary-button"
            disabled={loading}
          >
            {loading
              ? "Please wait..."
              : isRegistering
                ? "Create Account →"
                : "Login →"}
          </button>
        </form>

        {pendingEmail && !isRegistering && (
          <button
            type="button"
            className="secondary-button"
            style={{ width: "100%", marginTop: "14px" }}
            onClick={handleResendVerification}
            disabled={resendLoading}
          >
            {resendLoading ? "Sending..." : "Resend verification email"}
          </button>
        )}

        <div className="auth-switch">
          {isRegistering
            ? "Already have an account?"
            : "Don't have an account?"}
          <button
            type="button"
            onClick={() => {
              setIsRegistering(!isRegistering);
              setError("");
              setMessage("");
            }}
          >
            {isRegistering ? "Login" : "Create account"}
          </button>
        </div>
      </div>
    </div>
  );
}
