import { createContext, useContext, useEffect, useState } from "react";
import { auth as authApi, getToken, setToken } from "../lib/api";

/**
 * Real accounts on the backend: bcrypt-hashed passwords and a signed bearer
 * token. Only the token is kept in the browser; the profile is always asked
 * of the server, so a stale cached profile can never outlive its token.
 */
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      if (getToken()) {
        try {
          const me = await authApi.me();
          if (alive) setUser(me);
        } catch {
          setToken(null); // expired or revoked
        }
      }
      if (alive) setLoading(false);
    })();

    // Any request that comes back 401 signs the user out everywhere.
    const onSignedOut = () => setUser(null);
    window.addEventListener("roadguard:signed-out", onSignedOut);
    return () => {
      alive = false;
      window.removeEventListener("roadguard:signed-out", onSignedOut);
    };
  }, []);

  const login = async ({ email, password }) => {
    const res = await authApi.login({ email, password });
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  };

  const signup = async ({ name, email, password, city }) => {
    const res = await authApi.signup({ name, email, password, city: city || "Hyderabad" });
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  const updateProfile = async (patch) => {
    const me = await authApi.updateMe(patch);
    setUser(me);
    return me;
  };

  return (
    <AuthContext.Provider
      value={{
        user, loading, login, signup, logout, updateProfile,
        // Only ever the role the server put in the profile. The server
        // re-checks it on every request regardless of what this says.
        isOfficial: user?.role === "official",
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
