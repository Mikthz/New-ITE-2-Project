(function () {
    const theme = localStorage.getItem("theme") || "light";

    document.documentElement.classList.add("theme-loading");

    if (theme === "dark") {
        document.documentElement.classList.add("dark");
    } else {
        document.documentElement.classList.remove("dark");
    }

    window.addEventListener("DOMContentLoaded", function () {
        requestAnimationFrame(function () {
            document.documentElement.classList.remove("theme-loading");
        });
    });
})();