import Link from "next/link";
import { useRouter } from "next/router";
import { ReactNode, useState } from "react";

import { Me } from "../../lib/api";
import { Button } from "../ui/primitives";

type NavItem = { href: string; label: string };

function navForRole(role: Me["role"]): NavItem[] {
  const user: NavItem[] = [
    { href: "/dashboard", label: "Дашборд" },
    { href: "/tickets", label: "Мои заявки" },
    { href: "/tickets/new", label: "Создать заявку" },
  ];
  const support: NavItem[] = [
    { href: "/support", label: "Очередь поддержки" },
    { href: "/tickets", label: "Все заявки" },
  ];
  const admin: NavItem[] = [
    { href: "/admin/wizard", label: "Admin Wizard" },
    { href: "/admin/settings", label: "Настройки" },
    { href: "/admin/health", label: "Health" },
  ];

  if (role === "user") return user;
  if (role === "support") return [...user, ...support];
  return [...user, ...support, ...admin];
}

export default function AppShell({ me, children }: { me: Me; children: ReactNode }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const navItems = navForRole(me.role);

  function logout() {
    localStorage.removeItem("token");
    router.push("/");
  }

  return (
    <div className="appShell">
      <header className="topbar">
        <button className="ghostIconButton mobileOnly" onClick={() => setOpen((v) => !v)} aria-label="Открыть меню">
          ☰
        </button>
        <div className="brand">Support Portal</div>
        <div className="topbarRight">
          <span className="muted">{me.email}</span>
          <span className="roleBadge">{me.role}</span>
          <Button variant="secondary" onClick={logout}>
            Выйти
          </Button>
        </div>
      </header>
      <div className="shellBody">
        <aside className={`sidebar ${open ? "open" : ""}`}>
          <nav>
            {navItems.map((item) => (
              <Link key={item.href} href={item.href} className={router.pathname === item.href ? "navLink active" : "navLink"}>
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
