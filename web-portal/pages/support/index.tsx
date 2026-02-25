import AppShell from "../../components/layout/AppShell";
import SupportDashboard from "../../components/SupportDashboard";
import { EmptyState, Skeleton } from "../../components/ui/primitives";
import { useSession } from "../../lib/useSession";

export default function SupportPage() {
  const { me, loading } = useSession(true);

  if (loading || !me) {
    return (
      <main className="pageStandalone">
        <Skeleton height={32} />
      </main>
    );
  }

  if (me.role === "user") {
    return (
      <AppShell me={me}>
        <EmptyState title="Недостаточно прав" description="Очередь поддержки доступна ролям support и admin." />
      </AppShell>
    );
  }

  return (
    <AppShell me={me}>
      <SupportDashboard />
    </AppShell>
  );
}
