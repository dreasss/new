import { useEffect, useState } from "react";

import AppShell from "../../components/layout/AppShell";
import { Button, Card, EmptyState, ErrorState, Select, Skeleton, Textarea } from "../../components/ui/primitives";
import { ApiError, getAdminSetting, saveAdminSetting } from "../../lib/api";
import { useToast } from "../../lib/toast";
import { useSession } from "../../lib/useSession";

const sections = ["branding", "phrases", "telephony", "speechkit", "sso"];

export default function AdminSettingsPage() {
  const { me, loading: sessionLoading } = useSession(true);
  const { push } = useToast();
  const [section, setSection] = useState("branding");
  const [jsonText, setJsonText] = useState("{}");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const body = await getAdminSetting(section);
      setJsonText(JSON.stringify(body.config || {}, null, 2));
    } catch (err) {
      const e = err as ApiError;
      setError(e.message || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!sessionLoading && me?.role === "admin") {
      load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section, sessionLoading, me?.role]);

  async function save() {
    try {
      const parsed = JSON.parse(jsonText) as Record<string, unknown>;
      await saveAdminSetting(section, parsed);
      push("success", `Секция ${section} сохранена`);
    } catch (err) {
      if (err instanceof SyntaxError) {
        push("error", "JSON невалиден");
        return;
      }
      const e = err as ApiError;
      push("error", `Ошибка сохранения: ${e.message}`);
    }
  }

  if (sessionLoading || !me) return <main className="pageStandalone"><Skeleton height={36} /></main>;

  if (me.role !== "admin") {
    return (
      <AppShell me={me}>
        <EmptyState title="Недостаточно прав" description="Настройки доступны только роли admin." />
      </AppShell>
    );
  }

  return (
    <AppShell me={me}>
      <Card title="System Settings">
        <div className="toolbar">
          <Select value={section} onChange={(e) => setSection(e.target.value)}>
            {sections.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
          <Button variant="secondary" onClick={load}>Обновить</Button>
          <Button onClick={save}>Сохранить</Button>
        </div>

        {loading && <Skeleton height={180} />}
        {!loading && error && <ErrorState title="Ошибка секции" detail={error} onRetry={load} />}
        {!loading && !error && <Textarea rows={18} value={jsonText} onChange={(e) => setJsonText(e.target.value)} />}
      </Card>
    </AppShell>
  );
}
