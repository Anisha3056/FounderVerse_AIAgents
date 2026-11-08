const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/+$/, "");

async function request(endpoint, options = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  let data = {};

  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    const detail = data.detail;

    const error = new Error(
      (typeof detail === "string" ? detail : detail?.message) ||
        data.message ||
        `Request failed with status ${response.status}.`
    );

    error.status = response.status;
    error.code = detail?.code || data.code;
    error.usage = detail?.usage || data.usage;

    throw error;
  }

  return data;
}

// =====================================================
// AUTHENTICATION
// =====================================================

export async function registerUser(email, password) {
  return request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
    }),
  });
}

export async function loginUser(email, password) {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
    }),
  });
}

export async function getCurrentUser(token) {
  return request("/api/auth/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

// =====================================================
// COMPANY
// =====================================================

export async function createCompany(companyData, token) {
  return request("/api/companies/", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(companyData),
  });
}

export async function getCompany(companyId, token) {
  return request(`/api/companies/${companyId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

// =====================================================
// SIMULATION
// =====================================================

export async function getSimulationState(companyId, token) {
  return request(`/api/simulation/${companyId}/state`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function advanceSimulation(companyId, token) {
  return request(`/api/simulation/${companyId}/advance`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

// =====================================================
// AI BOARDROOM - MONTHLY USAGE
// =====================================================

export async function getBoardroomUsage(token) {
  return request("/api/boardroom/usage", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

// =====================================================
// AI BOARDROOM - ASK A QUESTION
// =====================================================

export async function askBoardroom(
  companyId,
  question,
  token,
  mode = "individual"
) {
  return request(`/api/boardroom/${companyId}/ask`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      question,
      mode,
    }),
  });
}

// =====================================================
// AI BOARDROOM - CONTINUE COLLABORATION
// =====================================================

export async function continueBoardroom(
  companyId,
  question,
  responses,
  token
) {
  return request(`/api/boardroom/${companyId}/continue`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      question,
      responses,
    }),
  });
}

// =====================================================
// FOUNDER DECISION
// =====================================================

export async function submitDecision(
  companyId,
  decisionData,
  token
) {
  return request(`/api/decisions/${companyId}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      company_id: companyId,
      ...decisionData,
    }),
  });
}

// =====================================================
// DECISION HISTORY
// =====================================================

export async function getDecisionHistory(
  companyId,
  token
) {
  return request(`/api/decisions/${companyId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}