/* Login controller — authenticates against the backend LDAP /login endpoint. */
(() => {
  const API = window.AGENTIC_API_URL || "/api";
  const $ = (id) => document.getElementById(id);

  const form = $("loginForm");
  const btn = $("loginBtn");
  const errorBox = $("loginError");

  function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
  }

  function clearError() {
    errorBox.textContent = "";
    errorBox.classList.add("hidden");
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearError();

    const username = $("username").value.trim();
    const password = $("password").value;
    if (!username || !password) {
      showError("Please enter your email and password.");
      return;
    }

    btn.disabled = true;
    btn.textContent = "Signing in…";

    try {
      const res = await fetch(`${API}/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        let detail = "Invalid credentials";
        try { detail = (await res.json()).error || detail; } catch { /* ignore */ }
        showError(detail);
        return;
      }

      // Authenticated — go to the review app.
      window.location.href = "/";
    } catch (err) {
      showError(`Could not reach the login service: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = "Sign in";
    }
  });
})();
