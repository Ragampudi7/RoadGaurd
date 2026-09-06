import { createContext, useContext, useEffect, useState } from "react";

/**
 * MOCK AUTH — deliberately not security.
 *
 * This gates navigation, not data: the "session" is a localStorage key anyone
 * can set from devtools, and there is no server verifying anything. It exists
 * so the app shell, ProtectedRoute and profile screens can be built now. Real
 * accounts arrive with the database, which is where users can actually live.
 */
const KEY = "roadguard_user";
const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) setUser(JSON.parse(raw));
    } catch {
      /* private mode, cleared storage, corrupt JSON — start signed out */
    }
    setReady(true);
  }, []);

  function persist(u) {
    setUser(u);
    try {
      if (u) localStorage.setItem(KEY, JSON.stringify(u));
      else localStorage.removeItem(KEY);
    } catch { /* storage unavailable; session is in-memory only */ }
  }

  const login = async ({ email }) => {
    const u = {
      id: "u_" + btoa(email).slice(0, 10).replace(/=/g, ""),
      name: email.split("@")[0].replace(/[._-]/g, " "),
      email,
      city: "Hyderabad",
      joined: new Date().toISOString(),
      mock: true,
    };
    persist(u);
    return u;
  };

  const signup = async ({ name, email }) => {
    const u = {
      id: "u_" + btoa(email).slice(0, 10).replace(/=/g, ""),
      name, email, city: "Hyderabad",
      joined: new Date().toISOString(), mock: true,
    };
    persist(u);
    return u;
  };

  const updateProfile = (patch) => persist({ ...user, ...patch });
  const logout = () => persist(null);

  return (
    <AuthCtx.Provider value={{ user, ready, login, signup, logout, updateProfile }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
