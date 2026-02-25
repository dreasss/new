import { useRouter } from "next/router";
import { FormEvent, useCallback, useEffect, useState } from "react";

import AppShell from "../../components/layout/AppShell";
import { Badge, Button, Card, EmptyState, ErrorState, Select, Skeleton, Textarea } from "../../components/ui/primitives";
import {
  addTicketComment,
  ApiError,
  closeTicket,
  fetchTicket,
  fetchTicketComments,
  fetchTicketHistory,
  HistoryItem,
  rateTicket,
  Ticket,
  CommentItem,
} from "../../lib/api";
import { useToast } from "../../lib/toast";
import { useSession } from "../../lib/useSession";

export default function TicketPage() {
  const router = useRouter();
  const id = String(router.query.id || "");
  const { me, loading: sessionLoading } = useSession(true);
  const { push } = useToast();

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [commentText, setCommentText] = useState("");
  const [rating, setRating] = useState("5");
  const [ratingComment, setRatingComment] = useState("");

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError("");
    try {
      const [t, c, h] = await Promise.all([fetchTicket(id), fetchTicketComments(id), fetchTicketHistory(id)]);
      setTicket(t);
      setComments(c.items);
      setHistory(h);
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

  async function onAddComment(e: FormEvent) {
    e.preventDefault();
    if (!commentText.trim()) return;
    try {
      await addTicketComment(id, commentText.trim());
      setCommentText("");
      push("success", "Комментарий добавлен");
      await load();
    } catch (err) {
      const eApi = err as ApiError;
      push("error", `Ошибка комментария: ${eApi.message}`);
    }
  }

  async function onClose() {
    try {
      await closeTicket(id, "Закрыто через портал");
      push("success", "Заявка закрыта");
      await load();
    } catch (err) {
      const eApi = err as ApiError;
      push("error", `Ошибка закрытия: ${eApi.message}`);
    }
  }

  async function onRate() {
    try {
      await rateTicket(id, Number(rating), ratingComment.trim());
      push("success", "Оценка сохранена");
    } catch (err) {
      const eApi = err as ApiError;
      push("error", `Ошибка оценки: ${eApi.message}`);
    }
  }

  if (sessionLoading || !me) {
    return (
      <main className="pageStandalone">
        <Skeleton height={30} />
      </main>
    );
  }

  return (
    <AppShell me={me}>
      {loading && (
        <div className="stack12">
          <Skeleton height={40} />
          <Skeleton height={180} />
        </div>
      )}
      {!loading && error && <ErrorState title="Ошибка заявки" detail={error} onRetry={load} />}
      {!loading && !error && !ticket && <EmptyState title="Заявка не найдена" description="Проверьте номер заявки." />}

      {!loading && !error && ticket && (
        <div className="stack24">
          <Card title={`Заявка #${ticket.id}`} actions={<Badge status={ticket.status} />}>
            <h2>{ticket.subject}</h2>
            <p>{ticket.description}</p>
            <div className="inlineActions">
              <Button variant="secondary" onClick={onClose}>Закрыть заявку</Button>
            </div>
            {ticket.status === "CLOSED" && (
              <div className="formGrid">
                <label>Оценка</label>
                <Select value={rating} onChange={(e) => setRating(e.target.value)}>
                  <option value="5">5</option>
                  <option value="4">4</option>
                  <option value="3">3</option>
                  <option value="2">2</option>
                  <option value="1">1</option>
                </Select>
                <label>Короткий отзыв</label>
                <Textarea rows={3} value={ratingComment} onChange={(e) => setRatingComment(e.target.value)} />
                <Button onClick={onRate}>Сохранить оценку</Button>
              </div>
            )}
          </Card>

          <Card title="История">
            {history.length === 0 ? (
              <EmptyState title="История пуста" description="События появятся после обработки заявки." />
            ) : (
              <ul className="timeline">
                {history.map((h) => (
                  <li key={h.id}>
                    <strong>{h.event_type}</strong>
                    <p className="muted">
                      {h.from_status || "—"} → {h.to_status || "—"}
                    </p>
                    <p>{h.message || "Без комментария"}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Комментарии">
            {comments.length === 0 ? (
              <EmptyState title="Комментариев пока нет" description="Добавьте комментарий, чтобы уточнить детали." />
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
            <form className="formStack" onSubmit={onAddComment}>
              <label htmlFor="comment">Новый комментарий</label>
              <Textarea id="comment" rows={3} value={commentText} onChange={(e) => setCommentText(e.target.value)} required />
              <Button type="submit">Отправить</Button>
            </form>
          </Card>
        </div>
      )}
    </AppShell>
  );
}
