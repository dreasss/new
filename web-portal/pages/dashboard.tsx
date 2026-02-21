import { useEffect, useState } from "react";
import { useRouter } from "next/router";

import AdminWizard from "../components/AdminWizard";
import SupportDashboard from "../components/SupportDashboard";
import UserDashboard from "../components/UserDashboard";
import { apiGet } from "../lib/api";

type Me = { id: number; email: string; role: "user" | "support" | "admin" };

export default function DashboardPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [alert, setAlert] = useState("Загрузка...");

  useEffect(() => {
    (async () => {
      const resp = await apiGet("/api/v1/auth/me");
      if (!resp.ok) {
        setAlert("Сессия невалидна, выполните вход");
        return;
      }
      const data = await resp.json();
      setMe(data);
      setAlert("");
    })();
  }, []);

  function logout() {
    localStorage.removeItem("token");
    router.push("/");
  }

  return (
    <main>
      <h1>Support Portal Dashboard</h1>
      {me && (
        <p>
          Вы: {me.email} ({me.role}) <button onClick={logout}>Выйти</button>
        </p>
      )}
      {alert && <p>{alert}</p>}
      {me?.role === "user" && <UserDashboard />}
      {(me?.role === "support" || me?.role === "admin") && <SupportDashboard />}
      {me?.role === "admin" && <AdminWizard />}
    </main>
  );
}
