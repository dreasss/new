import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { ApiError, createTicket, fetchMyTickets, Ticket } from "../lib/api";
import { useToast } from "../lib/toast";
import { Badge, Button, Card, EmptyState, ErrorState, Input, Select, Skeleton, Textarea } from "./ui/primitives";

export default function UserDashboard() {
  const { push } = useToast();
  const [items, setItems] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [channel, setChannel] = useState("");
  const [search, setSearch] = useState("");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const body = await fetchMyTickets({ status, channel, search });
      setItems(body.items);
    } catch (err) {
      const e = err as ApiError;
      setError(e.message || "Ошибка загрузки заявок");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, channel]);

  const canCreate = useMemo(() => subject.trim().length >= 8 && description.trim().length >= 20, [subject, description]);

  async function onCreateTicket(e: FormEvent) {
    e.preventDefault();
    if (!canCreate) {
      push("error", "Тема минимум 8 символов, описание минимум 20.");
      return;
    }
    setCreating(true);
    try {
      await createTicket({ subject: subject.trim(), description: description.trim(), channel: "web" });
      setSubject("");
      setDescription("");
      push("success", "Заявка создана");
      await load();
    } catch (err) {
      const eApi = err as ApiError;
      push("error", `Ошибка создания: ${eApi.message}`);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="stack24">
      <Card title="Создать заявку">
        <form className="formStack" onSubmit={onCreateTicket}>
          <label htmlFor="subject">Тема</label>
          <Input
            id="subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Например: Не работает сетевой диск"
            required
          />
          <small className="muted">От 8 до 120 символов.</small>
          <label htmlFor="description">Описание</label>
          <Textarea
            id="description"
            rows={5}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Опишите проблему, когда началась и что уже пробовали"
            required
          />
          <small className="muted">Минимум 20 символов. Это ускорит решение.</small>
          <Button type="submit" disabled={creating}>
            {creating ? "Создаём..." : "Создать заявку"}
          </Button>
        </form>
      </Card>

      <Card title="Мои заявки">
        <div className="toolbar">
          <Input
            placeholder="Поиск по теме"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Поиск по теме"
          />
          <Select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Фильтр по статусу">
            <option value="">Все статусы</option>
            <option value="NEW">NEW</option>
            <option value="IN_PROGRESS">IN_PROGRESS</option>
            <option value="WAITING_USER">WAITING_USER</option>
            <option value="DELEGATED">DELEGATED</option>
            <option value="RESOLVED">RESOLVED</option>
            <option value="CLOSED">CLOSED</option>
          </Select>
          <Select value={channel} onChange={(e) => setChannel(e.target.value)} aria-label="Фильтр по каналу">
            <option value="">Все каналы</option>
            <option value="web">web</option>
            <option value="voice">voice</option>
          </Select>
          <Button variant="secondary" onClick={load}>
            Обновить
          </Button>
        </div>

        {loading && (
          <div className="stack12">
            <Skeleton height={40} />
            <Skeleton height={40} />
            <Skeleton height={40} />
          </div>
        )}

        {!loading && error && <ErrorState title="Не удалось загрузить заявки" detail={error} onRetry={load} />}

        {!loading && !error && items.length === 0 && (
          <EmptyState title="Заявок пока нет" description="Создайте первую заявку через форму выше." />
        )}

        {!loading && !error && items.length > 0 && (
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Тема</th>
                  <th>Статус</th>
                  <th>Канал</th>
                </tr>
              </thead>
              <tbody>
                {items.map((t) => (
                  <tr key={t.id}>
                    <td>
                      <Link href={`/tickets/${t.id}`} className="textLink">
                        #{t.id}
                      </Link>
                    </td>
                    <td>{t.subject}</td>
                    <td>
                      <Badge status={t.status} />
                    </td>
                    <td>{t.channel}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
