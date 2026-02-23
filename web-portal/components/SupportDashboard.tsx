# codex/define-architecture-for-support-system-cphd8w
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ApiError, assignSelf, fetchSupportTickets, setTicketStatus, Ticket } from "../lib/api";
import { useToast } from "../lib/toast";
import { Badge, Button, Card, EmptyState, ErrorState, Input, Select, Skeleton } from "./ui/primitives";

type ViewMode = "table" | "kanban";

const statusColumns = ["NEW", "IN_PROGRESS", "WAITING_USER", "RESOLVED"];

export default function SupportDashboard() {
  const { push } = useToast();
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [items, setItems] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [search, setSearch] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await fetchSupportTickets({ status_filter: statusFilter, channel: channelFilter, search });
      setItems(data.items);
    } catch (err) {
      const e = err as ApiError;
      setError(e.message || "Ошибка загрузки очереди");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, channelFilter]);

  async function onAssignSelf(ticketId: number) {
    try {
      await assignSelf(ticketId);
      push("success", `Заявка #${ticketId} назначена на вас`);
      await load();
    } catch (err) {
      const e = err as ApiError;
      push("error", `Ошибка назначения: ${e.message}`);
    }
  }

  async function onSetStatus(ticketId: number, status: string) {
    try {
      await setTicketStatus(ticketId, status);
      push("success", `Статус заявки #${ticketId} обновлён`);
      await load();
    } catch (err) {
      const e = err as ApiError;
      push("error", `Ошибка статуса: ${e.message}`);
    }
  }

  const kanban = useMemo(() => {
    const grouped: Record<string, Ticket[]> = {};
    statusColumns.forEach((key) => {
      grouped[key] = [];
    });
    items.forEach((item) => {
      if (grouped[item.status]) grouped[item.status].push(item);
    });
    return grouped;
  }, [items]);

  return (
    <Card
      title="Очередь поддержки"
      actions={
        <div className="inlineActions">
          <Button variant={viewMode === "table" ? "primary" : "secondary"} onClick={() => setViewMode("table")}>Таблица</Button>
          <Button variant={viewMode === "kanban" ? "primary" : "secondary"} onClick={() => setViewMode("kanban")}>Канбан</Button>
        </div>
      }
    >
      <div className="toolbar">
        <Input placeholder="Поиск по теме" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Поиск" />
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Статус">
          <option value="">Все статусы</option>
          <option value="NEW">NEW</option>
          <option value="IN_PROGRESS">IN_PROGRESS</option>
          <option value="WAITING_USER">WAITING_USER</option>
          <option value="DELEGATED">DELEGATED</option>
          <option value="RESOLVED">RESOLVED</option>
          <option value="CLOSED">CLOSED</option>
        </Select>
        <Select value={channelFilter} onChange={(e) => setChannelFilter(e.target.value)} aria-label="Канал">
          <option value="">Все каналы</option>
          <option value="web">web</option>
          <option value="voice">voice</option>
        </Select>
        <Button variant="secondary" onClick={load}>Обновить</Button>
      </div>

      {loading && (
        <div className="stack12">
          <Skeleton height={42} />
          <Skeleton height={42} />
          <Skeleton height={42} />
        </div>
      )}

      {!loading && error && <ErrorState title="Ошибка очереди" detail={error} onRetry={load} />}

      {!loading && !error && items.length === 0 && (
        <EmptyState title="Очередь пуста" description="Нет заявок под текущими фильтрами." />
      )}

      {!loading && !error && items.length > 0 && viewMode === "table" && (
        <div className="tableWrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Тема</th>
                <th>Статус</th>
                <th>Канал</th>
                <th>Исполнитель</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {items.map((t) => (
                <tr key={t.id}>
                  <td>
                    <Link href={`/support/tickets/${t.id}`} className="textLink">#{t.id}</Link>
                  </td>
                  <td>{t.subject}</td>
                  <td><Badge status={t.status} /></td>
                  <td>{t.channel}</td>
                  <td>{t.assigned_user_id ? `#${t.assigned_user_id}` : "—"}</td>
                  <td>
                    <div className="inlineActions">
                      <Button variant="secondary" onClick={() => onAssignSelf(t.id)}>Взять</Button>
                      <Select defaultValue={t.status} onChange={(e) => onSetStatus(t.id, e.target.value)}>
                        <option value="IN_PROGRESS">IN_PROGRESS</option>
                        <option value="WAITING_USER">WAITING_USER</option>
                        <option value="DELEGATED">DELEGATED</option>
                        <option value="RESOLVED">RESOLVED</option>
                        <option value="CLOSED">CLOSED</option>
                      </Select>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && !error && items.length > 0 && viewMode === "kanban" && (
        <div className="kanbanGrid">
          {statusColumns.map((status) => (
            <div key={status} className="kanbanCol">
              <h4>{status}</h4>
              {kanban[status].length === 0 ? (
                <p className="muted">Нет заявок</p>
              ) : (
                kanban[status].map((t) => (
                  <article key={t.id} className="kanbanCard">
                    <Link href={`/support/tickets/${t.id}`} className="textLink">#{t.id} {t.subject}</Link>
                    <p className="muted">Канал: {t.channel}</p>
                  </article>
                ))
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
=======
import { FormEvent, useCallback, useEffect, useState } from "react";

import { apiGet, apiPost } from "../lib/api";

type Ticket = { id: number; subject: string; status: string; assigned_user_id: number | null; channel: string };

export default function SupportDashboard() {
  const [items, setItems] = useState<Ticket[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [alert, setAlert] = useState("");

  const load = useCallback(async () => {
    const qs = new URLSearchParams();
    if (statusFilter) qs.set("status_filter", statusFilter);
    if (channelFilter) qs.set("channel", channelFilter);
    const resp = await apiGet(`/api/v1/support/tickets?${qs.toString()}`);
    if (!resp.ok) {
      setAlert("Не удалось загрузить очередь");
      return;
    }
    const body = await resp.json();
    setItems(body.items);
  }, [statusFilter, channelFilter]);

  useEffect(() => {
    load();
  }, [load]);

  async function assignSelf(ticketId: number) {
    const resp = await apiPost(`/api/v1/tickets/${ticketId}/assign-self`, {});
    if (!resp.ok) {
      setAlert(`Ошибка назначения: ${await resp.text()}`);
      return;
    }
    setAlert(`Заявка #${ticketId} назначена`);
    await load();
  }

  async function setStatus(e: FormEvent<HTMLFormElement>, ticketId: number) {
    e.preventDefault();
    const target = e.currentTarget.elements.namedItem("status") as HTMLSelectElement;
    const resp = await apiPost(`/api/v1/tickets/${ticketId}/status`, { status: target.value });
    if (!resp.ok) {
      setAlert(`Ошибка статуса: ${await resp.text()}`);
      return;
    }
    setAlert(`Статус #${ticketId} обновлен`);
    await load();
  }

  return (
    <section>
      <h2>Очередь поддержки</h2>
      <label>Статус: </label>
      <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
        <option value="">Все</option>
        <option value="NEW">NEW</option>
        <option value="IN_PROGRESS">IN_PROGRESS</option>
        <option value="WAITING_USER">WAITING_USER</option>
        <option value="DELEGATED">DELEGATED</option>
        <option value="RESOLVED">RESOLVED</option>
        <option value="CLOSED">CLOSED</option>
      </select>
      <label> Канал: </label>
      <select value={channelFilter} onChange={(e) => setChannelFilter(e.target.value)}>
        <option value="">Все</option>
        <option value="web">web</option>
        <option value="voice">voice</option>
      </select>
      {alert && <p>{alert}</p>}
      <ul>
        {items.map((t) => (
          <li key={t.id}>
            #{t.id} {t.subject} [{t.status}] ({t.channel})
            <button onClick={() => assignSelf(t.id)}>Назначить себе</button>
            <form onSubmit={(e) => setStatus(e, t.id)}>
              <select name="status" defaultValue={t.status}>
                <option value="IN_PROGRESS">IN_PROGRESS</option>
                <option value="WAITING_USER">WAITING_USER</option>
                <option value="DELEGATED">DELEGATED</option>
                <option value="RESOLVED">RESOLVED</option>
                <option value="CLOSED">CLOSED</option>
              </select>
              <button type="submit">Сменить</button>
            </form>
          </li>
        ))}
      </ul>
    </section>
# main
  );
}
