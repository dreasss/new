import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/router";

import { API } from "../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      const resp = await fetch(`${API}/api/v1/public/branding`);
      if (!resp.ok) return;
      const body = await resp.json();
      const cfg = body.config || {};
      if (cfg.title) document.title = String(cfg.title);
      if (cfg.primaryColor) {
        document.documentElement.style.setProperty("--primary-color", String(cfg.primaryColor));
      }
    })();
  }, []);


  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    const response = await fetch(`${API}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      setError(`Login failed: ${await response.text()}`);
      return;
    }
    const data = await response.json();
    localStorage.setItem("token", data.access_token);
    await router.push("/dashboard");
  }

  async function ssoLogin() {
    const response = await fetch(`${API}/api/v1/auth/sso/login`);
    if (!response.ok) {
      setError(`SSO error: ${await response.text()}`);
      return;
    }
    const body = await response.json();
    window.location.href = body.redirect_url;
  }

  return (
    <main>
      <h1>Support Portal Login</h1>
      <form onSubmit={onSubmit}>
        <label>Email</label>
        <br />
        <input value={email} onChange={(e) => setEmail(e.target.value)} required />
        <br />
        <label>Password</label>
        <br />
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <br />
        <button type="submit">Локальный вход</button>
      </form>
      <hr />
      <button onClick={ssoLogin}>SSO вход (OIDC/SAML)</button>
      {error && <p>{error}</p>}
    </main>
  );
}
