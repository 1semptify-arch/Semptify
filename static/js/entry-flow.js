/**
 * Semptify Entry Flow Helper
 * Centralizes first-visit vs returning-user routing decisions.
 */

const SemptifyEntryFlow = {
    STATE_KEY: "semptify_entry_state_v1",
    COOKIE_NAME: "semptify_uid",

    getCookie(name) {
        const cookies = document.cookie ? document.cookie.split(";") : [];
        for (const cookie of cookies) {
            const [rawName, ...rest] = cookie.trim().split("=");
            if (rawName === name) {
                return decodeURIComponent(rest.join("="));
            }
        }
        return null;
    },

    getUserId() {
        if (window.SemptifyAuth && typeof window.SemptifyAuth.getUserId === "function") {
            return window.SemptifyAuth.getUserId();
        }
        return this.getCookie(this.COOKIE_NAME);
    },

    hasValidStorageUser(userId = this.getUserId()) {
        if (!userId || userId.length < 10) return false;
        const providerPrefix = userId.charAt(0).toUpperCase();
        return ["G", "D", "O"].includes(providerPrefix);
    },

    getRoleFromUserId(userId = this.getUserId()) {
        if (!userId || userId.length < 2) return null;
        const roleCode = userId.charAt(1).toUpperCase();
        const roleMap = {
            U: "user",
            V: "advocate",
            L: "legal",
            A: "admin",
            M: "manager",
        };
        return roleMap[roleCode] || null;
    },

    getRoleFallbackRoute(role = this.getRoleFromUserId()) {
        const fallback = {
            user: "/tenant",
            advocate: "/advocate",
            legal: "/legal",
            admin: "/admin",
            manager: "/admin",
        };
        return fallback[role] || "/ui/";
    },

    saveWelcomeState(role, storageState) {
        const payload = {
            role: role || "user",
            storage_state: storageState || "need_connect",
            ts: new Date().toISOString(),
            source_path: window.location.pathname,
        };

        try {
            localStorage.setItem(this.STATE_KEY, JSON.stringify(payload));
        } catch (_) {
            // Ignore storage errors in private mode.
        }

        return payload;
    },

    readWelcomeState() {
        try {
            const raw = localStorage.getItem(this.STATE_KEY);
            if (!raw) return null;
            const parsed = JSON.parse(raw);
            if (!parsed || typeof parsed !== "object") return null;
            return parsed;
        } catch (_) {
            return null;
        }
    },

    buildStorageConnectUrl(role, source = "welcome", returnTo = "") {
        const targetRole = role || this.getRoleFromUserId() || "user";
        const params = new URLSearchParams({
            role: targetRole,
            from: source,
        });
        if (returnTo && returnTo.startsWith("/") && !returnTo.startsWith("//")) {
            params.set("return_to", returnTo);
        }
        return "/storage/providers?" + params.toString();
    },

    async resolveStartDestination(role, storageState, nextRoute, source = "welcome") {
        const targetRoute = nextRoute || this.getRoleFallbackRoute(role);

        if (storageState === "need_connect") {
            return this.buildStorageConnectUrl(role, source, targetRoute);
        }

        if (storageState !== "already_connected") {
            return targetRoute;
        }

        try {
            const statusResponse = await fetch("/storage/status", {
                credentials: "include",
            });
            const statusData = await statusResponse.json();

            if (!statusData || !statusData.authenticated) {
                return this.buildStorageConnectUrl(role, source, targetRoute);
            }

            // Vault readiness is proven by function-token issuance.
            const tokenResponse = await fetch("/storage/function-token/issue", {
                method: "POST",
                credentials: "include",
            });

            if (tokenResponse.ok) {
                return targetRoute;
            }

            return this.buildStorageConnectUrl(role, source, targetRoute);
        } catch (_) {
            return this.buildStorageConnectUrl(role, source, targetRoute);
        }
    },

    redirectReturningUser(options = {}) {
        const {
            target = "/ui/",
            fallback = this.getRoleFallbackRoute(),
            includeSearch = true,
        } = options;

        if (!this.hasValidStorageUser()) {
            return false;
        }

        const current = window.location.pathname;
        const allowedPaths = new Set(["/", "/index.html", "/static/welcome.html", "/welcome.html"]);
        if (!allowedPaths.has(current)) {
            return false;
        }

        const destination = target || fallback;
        if (!destination || destination === current) {
            return false;
        }

        const suffix = includeSearch ? "?from=welcome" : "";
        window.location.replace(destination + suffix);
        return true;
    },
};

window.SemptifyEntryFlow = SemptifyEntryFlow;
