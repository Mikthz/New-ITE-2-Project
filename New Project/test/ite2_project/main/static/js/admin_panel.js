(function () {
    function setTheme(theme) {
        const safeTheme = theme === "dark" ? "dark" : "light";
        const root = document.documentElement;
        const body = document.body;

        root.classList.add("theme-loading");
        root.classList.toggle("dark", safeTheme === "dark");
        root.dataset.theme = safeTheme;

        if (body) {
            body.classList.remove("theme-dark", "theme-light");
            body.classList.add(safeTheme === "dark" ? "theme-dark" : "theme-light");
        }

        localStorage.setItem("appTheme", safeTheme);
        localStorage.removeItem("theme");

        document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
            const isActive = button.dataset.themeToggle === safeTheme;
            button.classList.toggle("ring-2", isActive);
            button.classList.toggle("ring-cyan-400", isActive && safeTheme === "dark");
            button.classList.toggle("ring-orange-400", isActive && safeTheme === "light");
        });

        document.querySelectorAll("[data-press-theme]").forEach(function (button) {
            if (typeof button.applyPressableStyle === "function") {
                button.applyPressableStyle();
            }
        });

        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                root.classList.remove("theme-loading");
            });
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

        function setupPressableButtons() {
            const isDarkMode = function () {
                return document.documentElement.classList.contains("dark") ||
                    document.documentElement.dataset.theme === "dark" ||
                    document.body.classList.contains("theme-dark");
            };

            const getButtonTheme = function (isIconOnly, button) {
                const forcedTheme = button ? button.dataset.pressTheme : "";

                const useDarkTheme =
                    forcedTheme === "dark" ||
                    (!forcedTheme && isDarkMode());

                if (useDarkTheme) {
                    return {
                        raised: isIconOnly
                            ? "0 4px 0 #0e7490, 0 7px 11px rgba(8, 145, 178, 0.24)"
                            : "0 5px 0 #0e7490, 0 10px 16px rgba(8, 145, 178, 0.24)",
                        raisedHover: isIconOnly
                            ? "0 4px 0 #155e75, 0 7px 11px rgba(8, 145, 178, 0.28)"
                            : "0 5px 0 #155e75, 0 10px 16px rgba(8, 145, 178, 0.28)",
                        pressed: isIconOnly
                            ? "0 1px 0 #155e75, 0 3px 6px rgba(8, 145, 178, 0.18)"
                            : "0 1px 0 #155e75, 0 4px 8px rgba(8, 145, 178, 0.18)"
                    };
                }

                return {
                    raised: isIconOnly
                        ? "0 4px 0 #c2410c, 0 7px 11px rgba(194, 65, 12, 0.22)"
                        : "0 5px 0 #c2410c, 0 10px 16px rgba(194, 65, 12, 0.22)",
                    raisedHover: isIconOnly
                        ? "0 4px 0 #9a3412, 0 7px 11px rgba(194, 65, 12, 0.26)"
                        : "0 5px 0 #9a3412, 0 10px 16px rgba(194, 65, 12, 0.26)",
                    pressed: isIconOnly
                        ? "0 1px 0 #9a3412, 0 3px 6px rgba(194, 65, 12, 0.16)"
                        : "0 1px 0 #9a3412, 0 4px 8px rgba(194, 65, 12, 0.16)"
                };
            };

            const selector = [
                "button",
                "a.btn-primary",
                "a.btn-secondary",
                "a[href].rounded-xl",
                "a[href].rounded-2xl",
                "a[href].rounded-lg"
            ].join(",");

            const pressableButtons = [];

            document.querySelectorAll(selector).forEach(function (button) {
                if (
                    button.closest("#sidebar") ||
                    button.classList.contains("sidebar-link") ||
                    button.classList.contains("sidebar-sublink") ||
                    button.classList.contains("login-3d-button") ||
                    button.classList.contains("no-press-effect") ||
                    button.dataset.noPress === "true"
                ) {
                    return;
                }

                button.classList.add("pressable-button");

                const rect = button.getBoundingClientRect();
                const isIconOnly =
                    rect.width <= 48 && rect.height <= 48 ||
                    button.querySelector("i") && button.textContent.trim() === "";

                if (isIconOnly) {
                    button.classList.add("pressable-icon");
                }

                const applyRaisedStyle = function () {
                    const theme = getButtonTheme(isIconOnly, button);

                    button.style.transform = "translateY(0)";
                    button.style.boxShadow = button.matches(":hover")
                        ? theme.raisedHover
                        : theme.raised;

                    if (button.dataset.pressTheme === "light") {
                        button.style.setProperty("background-color", "#ffffff", "important");
                        button.style.setProperty("border-color", "#fed7aa", "important");
                        button.style.setProperty("color", "#334155", "important");
                    } else if (button.dataset.pressTheme === "dark") {
                        button.style.setProperty("background-color", "#334155", "important");
                        button.style.setProperty("border-color", "#475569", "important");
                        button.style.setProperty("color", "#f1f5f9", "important");
                    }

                    if (button.dataset.pressTheme === "light") {
                        button.style.setProperty("background-color", "#ffffff", "important");
                        button.style.setProperty("border-color", "#fed7aa", "important");
                        button.style.setProperty("color", "#334155", "important");

                        button.querySelectorAll("i").forEach(function (icon) {
                            icon.style.setProperty("color", "#f97316", "important");
                        });

                    } else if (button.dataset.pressTheme === "dark") {
                        button.style.setProperty("background-color", "#334155", "important");
                        button.style.setProperty("border-color", "#475569", "important");
                        button.style.setProperty("color", "#f1f5f9", "important");

                        button.querySelectorAll("i").forEach(function (icon) {
                            icon.style.setProperty("color", "#67e8f9", "important");
                        });
                    }
                };

                const applyPressedStyle = function () {
                    const theme = getButtonTheme(isIconOnly, button);

                    button.style.transform = isIconOnly
                        ? "translateY(3px)"
                        : "translateY(4px)";

                    button.style.boxShadow = theme.pressed;
                };

                const pressButton = function () {
                    button.classList.add("is-pressed");
                    applyPressedStyle();
                };

                const releaseButton = function () {
                    button.classList.remove("is-pressed");
                    applyRaisedStyle();
                };

                applyRaisedStyle();

                button.addEventListener("mouseenter", function () {
                    if (!button.classList.contains("is-pressed")) {
                        applyRaisedStyle();
                    }
                });

                button.addEventListener("mouseleave", releaseButton);
                button.addEventListener("pointerdown", pressButton);
                button.addEventListener("pointerup", releaseButton);
                button.addEventListener("pointercancel", releaseButton);

                button.addEventListener("keydown", function (event) {
                    if (event.key === " " || event.key === "Enter") {
                        pressButton();
                    }
                });

                button.addEventListener("keyup", function (event) {
                    if (event.key === " " || event.key === "Enter") {
                        releaseButton();
                    }
                });

                pressableButtons.push({
                    button: button,
                    applyRaisedStyle: applyRaisedStyle
                });

                button.applyPressableStyle = applyRaisedStyle;
            });

            const themeObserver = new MutationObserver(function () {
                pressableButtons.forEach(function (item) {
                    if (!item.button.classList.contains("is-pressed")) {
                        item.applyRaisedStyle();
                    }
                });
            });

            themeObserver.observe(document.documentElement, {
                attributes: true,
                attributeFilter: ["class", "data-theme"]
            });

            themeObserver.observe(document.body, {
                attributes: true,
                attributeFilter: ["class"]
            });
        }


    function setupPageTransitions() {
        const content = document.getElementById("pageTransitionContent");
        const sidebar = document.getElementById("sidebar");

        if (!content || !sidebar) return;

        const sidebarLinks = Array.from(
            sidebar.querySelectorAll("a[href]")
        ).filter(function (link) {
            const href = link.getAttribute("href");
            return href &&
                href !== "#" &&
                !href.startsWith("javascript:");
        });

        const normalizePath = function (url) {
            const parsedUrl = new URL(url, window.location.origin);
            return parsedUrl.pathname.replace(/\/+$/, "") || "/";
        };

        const getCurrentOrder = function () {
            const currentPath = normalizePath(window.location.href);

            const currentIndex = sidebarLinks.findIndex(function (link) {
                return normalizePath(link.href) === currentPath;
            });

            if (currentIndex !== -1) {
                return currentIndex;
            }

            const storedOrder = parseInt(sessionStorage.getItem("pageTransitionOrder") || "0", 10);
            return Number.isNaN(storedOrder) ? 0 : storedOrder;
        };

        const entryDirection = sessionStorage.getItem("pageTransitionDirection");

        if (entryDirection === "up") {
            content.classList.add("page-slide-in-up");
        } else if (entryDirection === "down") {
            content.classList.add("page-slide-in-down");
        }

        sessionStorage.removeItem("pageTransitionDirection");

        sidebarLinks.forEach(function (link, index) {
            link.dataset.navOrder = String(index);

            link.addEventListener("click", function (event) {
                const isModifiedClick =
                    event.ctrlKey ||
                    event.metaKey ||
                    event.shiftKey ||
                    event.altKey ||
                    event.button !== 0;

                if (
                    isModifiedClick ||
                    link.target === "_blank" ||
                    normalizePath(link.href) === normalizePath(window.location.href)
                ) {
                    return;
                }

                event.preventDefault();

                const currentOrder = getCurrentOrder();
                const direction = index > currentOrder ? "up" : "down";

                sessionStorage.setItem("pageTransitionDirection", direction);
                sessionStorage.setItem("pageTransitionOrder", String(index));

                content.classList.remove("page-slide-out-up", "page-slide-out-down");
                content.classList.add(
                    direction === "up"
                        ? "page-slide-out-up"
                        : "page-slide-out-down"
                );

                window.setTimeout(function () {
                    window.location.href = link.href;
                }, 140);
            });
        });

        sessionStorage.setItem("pageTransitionOrder", String(getCurrentOrder()));
    }

    document.addEventListener("DOMContentLoaded", function () {
        setTheme(localStorage.getItem("appTheme") || "light");
        setupPressableButtons();
        setupPageTransitions();

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
