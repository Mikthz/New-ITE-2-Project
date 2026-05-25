(function () {
    const storedTheme = localStorage.getItem("appTheme") || localStorage.getItem("theme") || "light";
    const safeTheme = storedTheme === "dark" ? "dark" : "light";
    const root = document.documentElement;

    localStorage.setItem("appTheme", safeTheme);
    localStorage.removeItem("theme");

    root.classList.add("theme-loading");
    root.classList.toggle("dark", safeTheme === "dark");
    root.dataset.theme = safeTheme;

    function syncBodyTheme() {
        if (!document.body) return;
        document.body.classList.remove("theme-dark", "theme-light");
        document.body.classList.add(safeTheme === "dark" ? "theme-dark" : "theme-light");
    }

    if (document.readyState === "loading") {
        window.addEventListener("DOMContentLoaded", syncBodyTheme);
    } else {
        syncBodyTheme();
    }

    window.addEventListener("load", function () {
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                root.classList.remove("theme-loading");
            });
        });
    });
})();
