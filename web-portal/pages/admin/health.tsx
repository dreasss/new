import { useEffect, useState } from "react";

import AppShell from "../../components/layout/AppShell";
import { API } from "../../lib/api";
import { Button, Card, EmptyState, Skeleton } from "../../components/ui/primitives";
import { useSession } from "../../lib/useSession";

type HealthItem = { name: string; url: string; status: string; detail: string };

const TELEPHONY_URL = process.env.NEXT_PUBLIC_TELEPHONY_BOT_URL || "http://localhost:8010";

export default function AdminHealthPage() {
  const { me, loading: sessionLoading } = useSession(true);
  const [items, setItems] = useState<HealthItem[]>([
    { name: "core-api", url: `${API}/health`, status: "pending", detail: "" },
    { name: "telephony-bot", url: `${TELEPHONY_URL}/health`, status: "pending", detail: "" },
  ]);
  const [loading, setLoading] = useState(false);

  async function checkHealth() {
    setLoading(true);
    const checked = await Promise.all(
      items.map(async (item) => {
        try {
          const resp = await fetch(item.url);
          const text = await resp.text();
          return {
            ...item,
            status: resp.ok ? "ok" : "error",
            detail: text,
          };
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          return {
            ...item,
            status: "error",
            detail: message,
          };
        }
      }),
    );
    setItems(checked);
    setLoading(false);
  }

  useEffect(() => {
    if (!sessionLoading && me?.role === "admin") {
      checkHealth();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionLoading, me?.role]);

  if (sessionLoading || !me) return <main className="pageStandalone"><Skeleton height={32} /></main>;

  if (me.role !== "admin") {
    return (
      <AppShell me={me}>
        <EmptyState title="Недостаточно прав" description="Health-панель доступна только роли admin." />
      </AppShell>
    );
  }

  return (
    <AppShell me={me}>
      <Card title="Health сервисов" actions={<Button onClick={checkHealth}>{loading ? "Проверяем..." : "Проверить снова"}</Button>}>
        <div className="tableWrap">
          <table>
            <thead>
              <tr>
                <th>Сервис</th>
                <th>URL</th>
                <th>Статус</th>
                <th>Детали</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.name}>
                  <td>{item.name}</td>
                  <td>{item.url}</td>
                  <td>{item.status}</td>
                  <td className="preCell">{item.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </AppShell>
  );
}
