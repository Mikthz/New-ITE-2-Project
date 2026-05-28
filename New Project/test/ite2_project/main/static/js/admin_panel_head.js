(function () {
    const storedTheme = localStorage.getItem("appTheme") || localStorage.getItem("theme") || "light";
    const safeTheme = storedTheme === "dark" ? "dark" : "light";

    localStorage.setItem("appTheme", safeTheme);
    localStorage.removeItem("theme");

    document.documentElement.classList.add("theme-loading");
    document.documentElement.classList.toggle("dark", safeTheme === "dark");
    document.documentElement.dataset.theme = safeTheme;

    window.addEventListener("DOMContentLoaded", function () {
        document.body.classList.toggle("theme-dark", safeTheme === "dark");
        document.body.classList.toggle("theme-light", safeTheme === "light");

        requestAnimationFrame(function () {
            document.documentElement.classList.remove("theme-loading");
        });
    });
})();
