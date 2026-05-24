(function () {
    function setTheme(theme) {
        const safeTheme = theme === "dark" ? "dark" : "light";
        document.body.classList.toggle("theme-dark", safeTheme === "dark");
        document.body.classList.toggle("theme-light", safeTheme === "light");
        document.documentElement.dataset.theme = safeTheme;
        localStorage.setItem("appTheme", safeTheme);

        document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
            const isActive = button.dataset.themeToggle === safeTheme;
            button.classList.toggle("ring-2", isActive);
            button.classList.toggle("ring-cyan-400", isActive);
            button.classList.toggle("ring-orange-400", isActive && safeTheme === "light");
        });
    }

    window.setAppTheme = setTheme;
    window.openSidebar = function () {
        const sidebar = document.getElementById("sidebar");
        const overlay = document.getElementById("sidebarOverlay");
        if (sidebar) sidebar.classList.remove("-translate-x-full");
        if (overlay) overlay.classList.remove("hidden");
    };
    window.closeSidebar = function () {
        const sidebar = document.getElementById("sidebar");
        const overlay = document.getElementById("sidebarOverlay");
        if (sidebar) sidebar.classList.add("-translate-x-full");
        if (overlay) overlay.classList.add("hidden");
    };
    window.closeAlert = function (id) {
        const alertBox = document.getElementById(id);
        if (alertBox) alertBox.remove();
    };

    document.addEventListener("DOMContentLoaded", function () {
        setTheme(localStorage.getItem("appTheme") || "light");

        document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
            button.addEventListener("click", function () {
                setTheme(button.dataset.themeToggle);
            });
        });

        const errorAlert = document.getElementById("errorAlert");
        if (errorAlert) {
            setTimeout(function () {
                errorAlert.style.opacity = "0";
                errorAlert.style.transform = "translate(-50%, -20px)";
                setTimeout(function () { errorAlert.remove(); }, 300);
            }, 5000);
        }

        const SEARCH_DELAY = 600;
        document.querySelectorAll("form[data-auto-search='true']").forEach(function (form) {
            const input = form.querySelector("input[name='search']");
            if (!input) return;
            let timer = null;
            input.addEventListener("input", function () {
                clearTimeout(timer);
                timer = setTimeout(function () {
                    const searchValue = input.value.trim();
                    if (searchValue === "") {
                        window.location.href = window.location.pathname;
                        return;
                    }
                    form.submit();
                }, SEARCH_DELAY);
            });
        });

        document.querySelectorAll(".search-select").forEach(function (select) {
            if (window.TomSelect && !select.tomselect) {
                new TomSelect(select, {
                    create: false,
                    sortField: { field: "text", direction: "asc" }
                });
            }
        });
    });
})();
