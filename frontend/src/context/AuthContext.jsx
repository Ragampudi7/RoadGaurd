import { createContext, useContext, useEffect, useState } from "react";
import { auth as authApi, getToken, setToken, USE_MOCK } from "../lib/api";

/**
 * Authentication.
 *
 * Two modes, and the difference is not cosmetic:
 *
 *   USE_MOCK=true   a localStorage profile. No password is checked and nothing
 *                   reaches a server; it gates navigation, not data. The UI
 *                   says so on the auth and profile screens.
 *   USE_MOCK=false  real accounts. bcrypt-hashed passwords, a signed token, and
 *                   reports owned by the account that filed them.
 */
const MOCK_KEY = "roadguard_user";
const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      if (USE_MOCK) {
        try {
          const raw = localStorage.getItem(MOCK_KEY);
          if (raw && alive) setUser(JSON.parse(raw));
        } catch { /* private mode or corrupt JSON — start signed out */ }
      } else if (getToken()) {
        // Resume the session by asking the server who this token belongs to,
        // rather than trusting a cached profile the token may no longer match.
        try {
          const me = await authApi.me();
          if (alive) setUser(me);
        } catch {
          setToken(null);       // expired or revoked
        }
      }
      if (alive) setReady(true);
    })();
    return () => { alive = false; };
  }, []);

  function persistMock(u) {
    setUser(u);
    try {
      if (u) localStorage.setItem(MOCK_KEY, JSON.stringify(u));
      else localStorage.removeItem(MOCK_KEY);
    } catch { /* storage unavailable; session stays in memory */ }
  }

  async function login({ email, password }) {
    setError(null);
    if (USE_MOCK) {
      const u = { id: "u_local", name: email.split("@")[0].replace(/[._-]/g, " "),
                  email, city: "Hyderabad", joined: new Date().toISOString(), mock: true };
      persistMock(u);
      return u;
    }
    const res = await authApi.login({ email, password });
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  }

  async function signup({ name, email, password, city }) {
    setError(null);
    if (USE_MOCK) {
      const u = { id: "u_local", name, email, city: city || "Hyderabad",
                  joined: new Date().toISOString(), mock: true };
      persistMock(u);
      return u;
    }
    const res = await authApi.signup({ name, email, password, city });
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  }

  async function updateProfile(patch) {
    if (USE_MOCK) return persistMock({ ...user, ...patch });
    const me = await authApi.updateMe(patch);
    setUser(me);
    return me;
  }

  function logout() {
    if (USE_MOCK) persistMock(null);
    else { setToken(null); setUser(null); }
  }

  return (
    <AuthCtx.Provider value={{
      user, ready, error, login, signup, logout, updateProfile, isMock: USE_MOCK,
      // The role decides which screens exist. It is only ever the one the
      // server put in the profile — there is no way to set it from here, and
      // the server re-checks on every request regardless of what this says.
      isOfficial: user?.role === "official",
    }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
