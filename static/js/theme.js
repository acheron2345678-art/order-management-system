(() => {
    const root = document.documentElement;

    function currentTheme() {
        return root.getAttribute("data-bs-theme") || "light";
    }

    function updateThemeButton() {
        const button = document.getElementById("theme-toggle");
        const icon = document.getElementById("theme-icon");

        if (!button) return;

        const dark = currentTheme() === "dark";
        if (icon) icon.textContent = dark ? "☀" : "☾";

        const label = dark ? "Switch to light mode" : "Switch to dark mode";
        button.setAttribute("aria-label", label);
        button.setAttribute("title", label);
    }

    document.addEventListener("DOMContentLoaded", () => {
        const button = document.getElementById("theme-toggle");
        updateThemeButton();

        if (!button) return;

        button.addEventListener("click", () => {
            const nextTheme = currentTheme() === "dark" ? "light" : "dark";
            root.setAttribute("data-bs-theme", nextTheme);
            localStorage.setItem("theme", nextTheme);
            updateThemeButton();
            window.dispatchEvent(new CustomEvent("themechange", { detail: { theme: nextTheme } }));
        });
    });
})();
