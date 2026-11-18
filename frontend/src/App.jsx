import { useEffect, useState } from "react";

import Login from "./pages/Login";
import CompanySetup from "./pages/CompanySetup";
import Landing from "./Landing";

import {
  getCurrentUser,
  getCompany,
} from "./services/api";

import FounderVerseDashboard from "./FounderVerseDashboard";


export default function App() {
  const [loading, setLoading] = useState(true);

  const [token, setToken] = useState(
    localStorage.getItem("founderverse_token")
  );

  const [user, setUser] = useState(null);
  const [company, setCompany] = useState(null);

  // A verification link must open the Login screen rather than the landing page.
  const [showLanding, setShowLanding] = useState(() => {
    return !new URLSearchParams(window.location.search).has("verify_email");
  });

  useEffect(() => {
    async function restoreSession() {
      // A verification link must be handled in the signed-out screen,
      // even if this browser currently has another user's session.
      const verificationLink = new URLSearchParams(
        window.location.search
      ).has("verify_email");

      if (verificationLink) {
        localStorage.removeItem("founderverse_token");
        localStorage.removeItem("founderverse_user_id");
        localStorage.removeItem("founderverse_company_id");
        setToken(null);
        setUser(null);
        setCompany(null);
        setShowLanding(false);
        setLoading(false);
        return;
      }

      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser(token);
        setUser(currentUser);

        if (currentUser.company_id) {
          const currentCompany = await getCompany(
            currentUser.company_id,
            token
          );
          setCompany(currentCompany);
        }
      } catch (error) {
        console.error("Session restoration failed:", error);

        localStorage.removeItem("founderverse_token");
        localStorage.removeItem("founderverse_user_id");
        localStorage.removeItem("founderverse_company_id");

        setToken(null);
        setUser(null);
        setCompany(null);
      } finally {
        setLoading(false);
      }
    }

    restoreSession();
  }, [token]);

  function handleLogin(result) {
    setToken(result.access_token);
    setUser({
      user_id: result.user_id,
      company_id: result.company_id,
    });
  }

  async function handleCompanyCreated(companyId) {
    try {
      const currentCompany = await getCompany(companyId, token);

      setUser((previous) => ({
        ...previous,
        company_id: companyId,
      }));

      setCompany(currentCompany);

      localStorage.setItem(
        "founderverse_company_id",
        companyId
      );
    } catch (error) {
      console.error("Failed to load created company:", error);
    }
  }

  if (loading) {
    return (
      <div className="loading-screen">
        Loading FounderVerse...
      </div>
    );
  }

  if (!token && showLanding) {
    return <Landing onEnter={() => setShowLanding(false)} />;
  }

  if (!token) {
    return <Login onLogin={handleLogin} />;
  }

  if (!user?.company_id) {
    return (
      <CompanySetup
        token={token}
        onCompanyCreated={handleCompanyCreated}
      />
    );
  }

  return (
    <FounderVerseDashboard
      token={token}
      user={user}
      company={company}
    />
  );
}
