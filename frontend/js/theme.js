(function () {
  const STORAGE_KEY = "td-theme";
  const root = document.documentElement;
  const media = window.matchMedia("(prefers-color-scheme: light)");
  let savedTheme = null;

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "dark" || stored === "light") savedTheme = stored;
  } catch (error) {
    savedTheme = null;
  }

  function getTheme() {
    return savedTheme || (media.matches ? "light" : "dark");
  }

  function applyTheme(theme, persist) {
    const next = theme === "light" ? "light" : "dark";
    root.dataset.theme = next;
    root.style.colorScheme = next;
    if (persist) {
      savedTheme = next;
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch (error) {
        savedTheme = next;
      }
    }
    window.dispatchEvent(new CustomEvent("td:theme", { detail: { theme: next } }));
    return next;
  }

  function toggle() {
    return applyTheme(getTheme() === "dark" ? "light" : "dark", true);
  }

  media.addEventListener("change", () => {
    if (!savedTheme) applyTheme(getTheme(), false);
  });
  window.addEventListener("storage", (event) => {
    if (event.key !== STORAGE_KEY) return;
    savedTheme = event.newValue === "light" || event.newValue === "dark" ? event.newValue : null;
    applyTheme(getTheme(), false);
  });

  applyTheme(getTheme(), false);
  window.TDTheme = { getTheme, toggle };
})();
