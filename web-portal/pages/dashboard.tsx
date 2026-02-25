import Link from "next/link";

import AppShell from "../components/layout/AppShell";
import { Card, EmptyState, ErrorState, Skeleton } from "../components/ui/primitives";
import { useSession } from "../lib/useSession";

export default function DashboardPage() {
  const { me, loading, error, reload } = useSession(true);

  if (loading) {
    return (
      <main className="pageStandalone">
        <Skeleton height={28} />
        <Skeleton height={120} />
      </main>
    );
  }

  if (!me) {
    return <ErrorState title="Ошибка доступа" detail={error || "Пользователь не найден"} onRetry={reload} />;
  }

  return (
    <AppShell me={me}>
      <div className="pageHeader">
        <h1>Дашборд</h1>
        <p className="muted">Рабочее место сотрудника техподдержки</p>
      </div>
      <div className="grid grid-3">
        <Card title="Мои заявки">
          <p>Просмотр и фильтрация ваших заявок.</p>
          <Link href="/tickets" className="textLink">
            Открыть список
          </Link>
        </Card>
        <Card title="Создание заявки">
          <p>Зарегистрируйте проблему с деталями и каналом.</p>
          <Link href="/tickets/new" className="textLink">
            Создать заявку
          </Link>
        </Card>
        {(me.role === "support" || me.role === "admin") && (
          <Card title="Очередь поддержки">
            <p>Работа с потоком обращений и SLA.</p>
            <Link href="/support" className="textLink">
              Открыть очередь
            </Link>
          </Card>
        )}
      </div>
      {me.role === "admin" ? (
        <div className="grid grid-2">
          <Card title="Администрирование">
            <ul>
              <li>
                <Link href="/admin/wizard" className="textLink">
                  Wizard настройки
                </Link>
              </li>
              <li>
                <Link href="/admin/settings" className="textLink">
                  Секции конфигурации
                </Link>
              </li>
              <li>
                <Link href="/admin/health" className="textLink">
                  Здоровье сервисов
                </Link>
              </li>
            </ul>
          </Card>
        </div>
      ) : (
        <EmptyState
          title="Дополнительные разделы"
          description="Административные разделы доступны только роли admin."
        />
      )}
    </AppShell>
  );
}
