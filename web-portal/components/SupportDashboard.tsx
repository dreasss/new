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
  );
}
