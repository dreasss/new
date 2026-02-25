import { useRouter } from "next/router";
import { FormEvent, useCallback, useEffect, useState } from "react";

import AppShell from "../../../components/layout/AppShell";
import { Badge, Button, Card, EmptyState, ErrorState, Select, Skeleton, Textarea } from "../../../components/ui/primitives";
import {
  addTicketComment,
  ApiError,
  assignSelf,
  fetchTicket,
  fetchTicketComments,
  setTicketStatus,
  Ticket,
  CommentItem,
} from "../../../lib/api";
import { useToast } from "../../../lib/toast";
import { useSession } from "../../../lib/useSession";

export default function SupportTicketDetailPage() {
  const { me, loading: sessionLoading } = useSession(true);
  const { push } = useToast();
  const router = useRouter();
  const id = String(router.query.id || "");

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [note, setNote] = useState("");
  const [nextStatus, setNextStatus] = useState("IN_PROGRESS");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError("");
    try {
      const [t, c] = await Promise.all([fetchTicket(id), fetchTicketComments(id)]);
      setTicket(t);
      setComments(c.items);
      setNextStatus(t.status === "NEW" ? "IN_PROGRESS" : t.status);
    } catch (err) {
      const e = err as ApiError;
      setError(e.message || "Ошибка загрузки заявки");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function onAssignSelf() {
    if (!ticket) return;
    try {
      await assignSelf(ticket.id);
      push("success", "Заявка назначена на вас");
      await load();
    } catch (err) {
      const e = err as ApiError;
      push("error", `Ошибка назначения: ${e.message}`);
    }
  }

  async function onSetStatus() {
    if (!ticket) return;
    try {
      await setTicketStatus(ticket.id, nextStatus);
      push("success", `Статус обновлён на ${nextStatus}`);
      await load();
    } catch (err) {
      const e = err as ApiError;
      push("error", `Ошибка статуса: ${e.message}`);
    }
  }

  async function onPublicReply(e: FormEvent) {
    e.preventDefault();
    if (!note.trim()) return;
    try {
      await addTicketComment(id, note.trim());
      setNote("");
      push("success", "Публичный ответ отправлен");
      await load();
    } catch (err) {
      const e = err as ApiError;
      push("error", `Ошибка ответа: ${e.message}`);
    }
  }

  if (sessionLoading || !me) {
    return (
      <main className="pageStandalone">
        <Skeleton height={32} />
      </main>
    );
  }

  if (me.role === "user") {
    return (
      <AppShell me={me}>
        <EmptyState title="Недостаточно прав" description="Карточка support-действий доступна support/admin." />
      </AppShell>
    );
  }

  return (
    <AppShell me={me}>
      {loading && <Skeleton height={160} />}
      {!loading && error && <ErrorState title="Ошибка загрузки" detail={error} onRetry={load} />}
      {!loading && !error && !ticket && <EmptyState title="Заявка не найдена" description="Проверьте идентификатор." />}
      {!loading && !error && ticket && (
        <div className="stack24">
          <Card title={`Support ticket #${ticket.id}`} actions={<Badge status={ticket.status} />}>
            <h2>{ticket.subject}</h2>
            <p>{ticket.description}</p>
            <div className="inlineActions">
              <Button variant="secondary" onClick={onAssignSelf}>Взять в работу</Button>
              <Select value={nextStatus} onChange={(e) => setNextStatus(e.target.value)}>
                <option value="IN_PROGRESS">IN_PROGRESS</option>
                <option value="WAITING_USER">WAITING_USER</option>
                <option value="DELEGATED">DELEGATED</option>
                <option value="RESOLVED">RESOLVED</option>
                <option value="CLOSED">CLOSED</option>
              </Select>
              <Button onClick={onSetStatus}>Применить статус</Button>
            </div>
          </Card>

          <Card title="Публичные комментарии">
            {comments.length === 0 ? (
              <EmptyState title="Комментариев нет" description="Отправьте первое сообщение пользователю." />
            ) : (
              <ul className="commentList">
                {comments.map((c) => (
                  <li key={c.id}>
                    <strong>Пользователь #{c.author_user_id}</strong>
                    <p>{c.content}</p>
                  </li>
                ))}
              </ul>
            )}
            <form className="formStack" onSubmit={onPublicReply}>
              <label htmlFor="reply">Публичный ответ</label>
              <Textarea id="reply" rows={4} value={note} onChange={(e) => setNote(e.target.value)} required />
              <Button type="submit">Ответить</Button>
            </form>
          </Card>
        </div>
      )}
    </AppShell>
  );
}
