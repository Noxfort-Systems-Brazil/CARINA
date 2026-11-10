// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type CcoThemeMode = 'light' | 'dark';

interface ThemeContextType {
  theme: CcoThemeMode;
  toggleTheme: () => void;
  isDark: boolean;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: 'light',
  toggleTheme: () => {},
  isDark: false,
});

const STORAGE_KEY = 'carina_cco_theme_mode';

export const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<CcoThemeMode>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(STORAGE_KEY) as CcoThemeMode | null;
      if (saved === 'dark' || saved === 'light') {
        return saved;
      }
    }
    return 'light'; // Default to CARINA official cartographic light theme (#F7F7F7)
  });

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, theme);
      if (theme === 'dark') {
        document.documentElement.classList.add('dark');
        document.body.style.backgroundColor = '#020617';
      } else {
        document.documentElement.classList.remove('dark');
        document.body.style.backgroundColor = '#F7F7F7';
      }
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, isDark: theme === 'dark' }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useCcoTheme = (): ThemeContextType => useContext(ThemeContext);
