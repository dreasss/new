import AppShell from "../../components/layout/AppShell";
import AdminWizard from "../../components/AdminWizard";
import { EmptyState, Skeleton } from "../../components/ui/primitives";
import { useSession } from "../../lib/useSession";

export default function AdminWizardPage() {
  const { me, loading } = useSession(true);

  if (loading || !me) {
    return (
      <main className="pageStandalone">
        <Skeleton height={40} />
      </main>
    );
  }

  if (me.role !== "admin") {
    return (
      <AppShell me={me}>
        <EmptyState title="Недостаточно прав" description="Wizard доступен только роли admin." />
      </AppShell>
    );
  }

  return (
    <AppShell me={me}>
      <AdminWizard />
    </AppShell>
  );
}
