"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

type ThemeContextValue = { isDark: boolean; toggleTheme: () => void };
const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    setIsDark(localStorage.getItem("researchiq-theme") === "dark");
  }, []);

  const toggleTheme = useCallback(() => setIsDark((current) => {
    const next = !current;
    localStorage.setItem("researchiq-theme", next ? "dark" : "light");
    return next;
  }), []);

  return <ThemeContext.Provider value={{ isDark, toggleTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const theme = useContext(ThemeContext);
  if (!theme) throw new Error("useTheme must be used inside ThemeProvider");
  return theme;
}
