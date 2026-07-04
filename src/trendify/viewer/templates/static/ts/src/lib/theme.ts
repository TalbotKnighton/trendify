/**
 * Light/dark/system theme selection. The actual pre-paint application of the stored theme
 * lives in a blocking inline <script> in base.html (must run synchronously before first paint
 * to avoid a flash of the wrong theme); this module owns the interactive selector afterward.
 */

const STORAGE_KEY = "trendify:theme";

export type ThemeChoice = "light" | "dark" | "system";

function prefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function getStoredTheme(): ThemeChoice {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "light" || stored === "dark" ? stored : "system";
}

export function applyTheme(choice: ThemeChoice): void {
  const isDark = choice === "dark" || (choice === "system" && prefersDark());
  document.documentElement.classList.toggle("dark", isDark);
}

export function setTheme(choice: ThemeChoice): void {
  if (choice === "system") {
    localStorage.removeItem(STORAGE_KEY);
  } else {
    localStorage.setItem(STORAGE_KEY, choice);
  }
  applyTheme(choice);
}

export interface ThemeComponent {
  theme: ThemeChoice;
  setTheme(choice: ThemeChoice): void;
}

export function themeSelector(): ThemeComponent {
  return {
    theme: getStoredTheme(),
    setTheme(choice: ThemeChoice) {
      this.theme = choice;
      setTheme(choice);
    },
  };
}
