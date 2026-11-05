import { useState } from "react";
import { loginUser, registerUser } from "../services/api";


export default function Login({ onLogin }) {

  const [isRegistering, setIsRegistering] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  async function handleSubmit(event) {

    event.preventDefault();

    setError("");
    setLoading(true);

    try {

      const result = isRegistering
        ? await registerUser(email, password)
        : await loginUser(email, password);

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

    } finally {

      setLoading(false);

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
              ? "Create your account and start building your SaaS company."
              : "Continue your startup journey."}
          </p>

        </div>


        <form onSubmit={handleSubmit}>

          <label>Email</label>

          <input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />


          <label>Password</label>

          <input
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />


          {error && (
            <div className="auth-error">
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


        <div className="auth-switch">

          {isRegistering
            ? "Already have an account?"
            : "Don't have an account?"}

          <button
            type="button"
            onClick={() => {
              setIsRegistering(!isRegistering);
              setError("");
            }}
          >
            {isRegistering ? "Login" : "Create account"}
          </button>

        </div>

      </div>

    </div>
  );
}