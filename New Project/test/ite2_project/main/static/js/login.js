document.addEventListener("DOMContentLoaded", function () {
    const errorPopup = document.getElementById("loginErrorPopup");
    const loginButton = document.querySelector(".login-3d-button");

    const isDarkMode = function () {
        return document.documentElement.classList.contains("dark") ||
            document.documentElement.dataset.theme === "dark" ||
            document.body.classList.contains("theme-dark");
    };

    if (errorPopup) {
        requestAnimationFrame(function () {
            errorPopup.classList.remove("max-h-0", "-translate-y-5", "opacity-0");
            errorPopup.classList.add("max-h-32", "translate-y-0", "opacity-100");
        });
    }

    if (!loginButton) return;

    const getButtonTheme = function () {
        if (isDarkMode()) {
            return {
                raised: "0 7px 0 #0e7490, 0 12px 20px rgba(8, 145, 178, 0.28)",
                raisedHover: "0 7px 0 #155e75, 0 12px 20px rgba(8, 145, 178, 0.32)",
                pressed: "0 1px 0 #155e75, 0 4px 10px rgba(8, 145, 178, 0.22)"
            };
        }

        return {
            raised: "0 7px 0 #c2410c, 0 12px 18px rgba(194, 65, 12, 0.24)",
            raisedHover: "0 7px 0 #9a3412, 0 12px 18px rgba(194, 65, 12, 0.28)",
            pressed: "0 1px 0 #9a3412, 0 4px 9px rgba(194, 65, 12, 0.18)"
        };
    };

    const applyRaisedStyle = function () {
        const theme = getButtonTheme();

        loginButton.style.transform = "translateY(0)";
        loginButton.style.boxShadow = loginButton.matches(":hover")
            ? theme.raisedHover
            : theme.raised;
    };

    const applyPressedStyle = function () {
        loginButton.style.transform = "translateY(6px)";
        loginButton.style.boxShadow = getButtonTheme().pressed;
    };

    const pressButton = function () {
        loginButton.classList.add("is-pressed");
        applyPressedStyle();
    };

    const releaseButton = function () {
        loginButton.classList.remove("is-pressed");
        applyRaisedStyle();
    };

    applyRaisedStyle();

    loginButton.addEventListener("mouseenter", function () {
        if (!loginButton.classList.contains("is-pressed")) {
            applyRaisedStyle();
        }
    });

    loginButton.addEventListener("mouseleave", releaseButton);
    loginButton.addEventListener("pointerdown", pressButton);
    loginButton.addEventListener("pointerup", releaseButton);
    loginButton.addEventListener("pointercancel", releaseButton);

    loginButton.addEventListener("keydown", function (event) {
        if (event.key === " " || event.key === "Enter") {
            pressButton();
        }
    });

    loginButton.addEventListener("keyup", function (event) {
        if (event.key === " " || event.key === "Enter") {
            releaseButton();
        }
    });

    const themeObserver = new MutationObserver(function () {
        if (!loginButton.classList.contains("is-pressed")) {
            applyRaisedStyle();
        }
    });

    themeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["class", "data-theme"]
    });

    themeObserver.observe(document.body, {
        attributes: true,
        attributeFilter: ["class"]
    });
});
