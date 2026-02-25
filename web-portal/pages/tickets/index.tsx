import AppShell from "../../components/layout/AppShell";
import UserDashboard from "../../components/UserDashboard";
import { Skeleton } from "../../components/ui/primitives";
import { useSession } from "../../lib/useSession";

export default function TicketsPage() {
  const { me, loading } = useSession(true);

  if (loading || !me) {
    return (
      <main className="pageStandalone">
        <Skeleton height={32} />
      </main>
    );
  }

  return (
    <AppShell me={me}>
      <UserDashboard />
    </AppShell>
  );
}
