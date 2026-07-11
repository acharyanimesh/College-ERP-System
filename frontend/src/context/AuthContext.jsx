import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import authAPI from "../api/auth";

/**
 * Session state for the whole app, replacing Django's request.user.
 * On load it asks the backend who is logged in (session cookie), and the
 * axiosClient's `api:unauthorized` event clears the user if the session
 * expires anywhere in the app.
 */
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // True until the initial /auth/me/ check resolves, so guards don't
  // bounce a logged-in user to the login page during a hard refresh.
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    authAPI
      .me()
      .then((profile) => {
        if (!cancelled) setUser(profile);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onUnauthorized = () => setUser(null);
    window.addEventListener("api:unauthorized", onUnauthorized);
    return () => window.removeEventListener("api:unauthorized", onUnauthorized);
  }, []);

  const login = useCallback(async (credentials) => {
    const profile = await authAPI.login(credentials);
    setUser(profile);
    return profile;
  }, []);

  /** Re-fetches /auth/me/ — used after actions that change fields on the
   * logged-in user object itself (e.g. requesting an email change) so the
   * UI reflects the new pending_email without a full reload. */
  const refreshUser = useCallback(async () => {
    const profile = await authAPI.me();
    setUser(profile);
    return profile;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authAPI.logout();
    } finally {
      // Even if the request fails the local session is gone (logout_user
      // in views.py redirects to "/" unconditionally too).
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
