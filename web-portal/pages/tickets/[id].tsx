import { useRouter } from "next/router";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { apiGet, apiPost } from "../../lib/api";

type Ticket = { id: number; subject: string; description: string; status: string };
type Comment = { id: number; author_user_id: number; content: string };

export default function TicketPage() {
  const router = useRouter();
  const id = router.query.id as string;
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [commentText, setCommentText] = useState("");
  const [rating, setRating] = useState("5");
  const [alert, setAlert] = useState("");

  const load = useCallback(async () => {
    if (!id) return;
    const t = await apiGet(`/api/v1/tickets/${id}`);
    const c = await apiGet(`/api/v1/tickets/${id}/comments`);
    if (t.ok) setTicket(await t.json());
    if (c.ok) setComments((await c.json()).items);
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function addComment(e: FormEvent) {
    e.preventDefault();
    const r = await apiPost(`/api/v1/tickets/${id}/comments`, { content: commentText });
    if (!r.ok) {
      setAlert(`Ошибка комментария: ${await r.text()}`);
      return;
    }
    setCommentText("");
    await load();
  }

  async function closeTicket() {
    const r = await apiPost(`/api/v1/tickets/${id}/close`, { resolution_comment: "Закрыто пользователем" });
    if (!r.ok) {
      setAlert(`Ошибка закрытия: ${await r.text()}`);
      return;
    }
    await load();
  }

  async function sendRating() {
    const r = await apiPost(`/api/v1/tickets/${id}/ratings`, { score: Number(rating), comment: "Оценка из портала" });
    if (!r.ok) {
      setAlert(`Ошибка оценки: ${await r.text()}`);
      return;
    }
    setAlert("Оценка сохранена");
  }

  return (
    <main>
      <h1>Заявка #{id}</h1>
      {ticket && (
        <>
          <p>
            {ticket.subject} [{ticket.status}]
          </p>
          <p>{ticket.description}</p>
          <button onClick={closeTicket}>Закрыть заявку</button>
          {ticket.status === "CLOSED" && (
            <div>
              <select value={rating} onChange={(e) => setRating(e.target.value)}>
                <option value="5">5</option>
                <option value="4">4</option>
                <option value="3">3</option>
                <option value="2">2</option>
                <option value="1">1</option>
              </select>
              <button onClick={sendRating}>Оценить</button>
            </div>
          )}
        </>
      )}

      <h3>Комментарии</h3>
      <ul>
        {comments.map((c) => (
          <li key={c.id}>
            {c.author_user_id}: {c.content}
          </li>
        ))}
      </ul>
      <form onSubmit={addComment}>
        <input value={commentText} onChange={(e) => setCommentText(e.target.value)} required />
        <button type="submit">Добавить комментарий</button>
      </form>
      {alert && <p>{alert}</p>}
    </main>
  );
}
