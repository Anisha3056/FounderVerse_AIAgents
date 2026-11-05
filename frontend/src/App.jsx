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

  const [showLanding, setShowLanding] = useState(true);



  useEffect(() => {

    async function restoreSession() {

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

    return (
      <Login onLogin={handleLogin} />
    );

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