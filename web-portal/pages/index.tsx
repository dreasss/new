import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/router";

# codex/define-architecture-for-support-system-cphd8w
import { ApiError, fetchBranding, login, API } from "../lib/api";
import { Button, Card, ErrorState, Input, Skeleton } from "../components/ui/primitives";
import { useToast } from "../lib/toast";

export default function LoginPage() {
  const router = useRouter();
  const { push } = useToast();
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("admin123");
  const [loading, setLoading] = useState(false);
  const [brandLoading, setBrandLoading] = useState(true);
  const [error, setError] = useState("");
  const [brandName, setBrandName] = useState("Support Portal");

  useEffect(() => {
    (async () => {
      try {
        const body = await fetchBranding();
        const cfg = body.config || {};
        if (typeof cfg.title === "string" && cfg.title.trim()) {
          setBrandName(cfg.title);
          document.title = cfg.title;
        }
        if (typeof cfg.primaryColor === "string" && cfg.primaryColor.trim()) {
          document.documentElement.style.setProperty("--primary-color", cfg.primaryColor);
        }
      } catch {
        setBrandName("Support Portal");
      } finally {
        setBrandLoading(false);
      }
    })();
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await login(email, password);
      localStorage.setItem("token", data.access_token);
      push("success", "Вход выполнен");
      await router.push("/dashboard");
    } catch (err) {
      const e = err as ApiError;
      setError(e.message || "Ошибка входа");
    } finally {
      setLoading(false);
    }
  }

  async function ssoLogin() {
    setError("");
    try {
      const response = await fetch(`${API}/api/v1/auth/sso/login`);
      const text = await response.text();
      if (!response.ok) {
        throw { message: text } as ApiError;
      }
      const body = JSON.parse(text) as { redirect_url: string };
      window.location.href = body.redirect_url;
    } catch (err) {
      const e = err as ApiError;
      setError(e.message || "Ошибка SSO");
    }
  }

  return (
    <main className="loginRoot">
      <Card title={brandLoading ? "Загрузка бренда..." : brandName}>
        {brandLoading ? (
          <Skeleton height={32} />
        ) : (
          <>
            <p className="muted">Вход через корпоративный аккаунт или dev-логин.</p>
            <form onSubmit={onSubmit} className="formStack">
              <label htmlFor="email">Email</label>
              <Input id="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              <label htmlFor="password">Пароль</label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              <Button type="submit" disabled={loading}>
                {loading ? "Входим..." : "Локальный вход"}
              </Button>
            </form>
            <div className="divider" />
            <Button variant="secondary" onClick={ssoLogin}>
              Вход через корпоративный аккаунт
            </Button>
            {error && <ErrorState title="Ошибка авторизации" detail={error} onRetry={() => setError("")} />}
          </>
        )}
      </Card>
=======
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
# main
    </main>
  );
}
