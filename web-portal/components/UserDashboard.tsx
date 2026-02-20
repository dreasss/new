import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { apiGet, apiPost } from "../lib/api";

type Ticket = { id: number; subject: string; status: string; channel: string };

export default function UserDashboard() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [alert, setAlert] = useState("");

  async function load() {
    const resp = await apiGet("/api/v1/tickets");
    if (!resp.ok) {
      setAlert("Не удалось загрузить заявки");
      return;
    }
    const body = await resp.json();
    setTickets(body.items);
  }

  useEffect(() => {
    load();
  }, []);

  async function createTicket(e: FormEvent) {
    e.preventDefault();
    const resp = await apiPost("/api/v1/tickets", { subject, description, channel: "web" });
    if (!resp.ok) {
      setAlert(`Ошибка создания: ${await resp.text()}`);
      return;
    }
    setSubject("");
    setDescription("");
    setAlert("Заявка создана");
    await load();
  }

  return (
    <section>
      <h2>Мои заявки</h2>
      <form onSubmit={createTicket}>
        <input placeholder="Тема" value={subject} onChange={(e) => setSubject(e.target.value)} required />
        <br />
        <textarea placeholder="Описание" value={description} onChange={(e) => setDescription(e.target.value)} required />
        <br />
        <button type="submit">Создать заявку</button>
      </form>
      {alert && <p>{alert}</p>}
      <ul>
        {tickets.map((t) => (
          <li key={t.id}>
            <Link href={`/tickets/${t.id}`}>#{t.id}</Link> — {t.subject} [{t.status}] ({t.channel})
          </li>
        ))}
      </ul>
    </section>
  );
}
