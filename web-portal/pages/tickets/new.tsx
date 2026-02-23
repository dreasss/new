import { FormEvent, useMemo, useState } from "react";

import AppShell from "../../components/layout/AppShell";
import { Button, Card, Input, Select, Textarea } from "../../components/ui/primitives";
import { createTicket } from "../../lib/api";
import { useToast } from "../../lib/toast";
import { useSession } from "../../lib/useSession";

export default function NewTicketPage() {
  const { me, loading } = useSession(true);
  const { push } = useToast();
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [channel, setChannel] = useState<"web" | "voice">("web");
  const [saving, setSaving] = useState(false);

  const valid = useMemo(() => subject.trim().length >= 8 && description.trim().length >= 20, [subject, description]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!valid) {
      push("error", "Заполните тему и описание корректно.");
      return;
    }
    setSaving(true);
    try {
      await createTicket({ subject: subject.trim(), description: description.trim(), channel });
      setSubject("");
      setDescription("");
      push("success", "Заявка создана");
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      push("error", `Ошибка создания: ${message}`);
    } finally {
      setSaving(false);
    }
  }

  if (loading || !me) return null;

  return (
    <AppShell me={me}>
      <Card title="Создать заявку">
        <form className="formStack" onSubmit={onSubmit}>
          <label htmlFor="subject">Тема</label>
          <Input id="subject" value={subject} onChange={(e) => setSubject(e.target.value)} required />
          <label htmlFor="description">Описание</label>
          <Textarea id="description" rows={6} value={description} onChange={(e) => setDescription(e.target.value)} required />
          <label htmlFor="channel">Канал</label>
          <Select id="channel" value={channel} onChange={(e) => setChannel(e.target.value as "web" | "voice")}>
            <option value="web">web</option>
            <option value="voice">voice</option>
          </Select>
          <Button type="submit" disabled={saving}>{saving ? "Сохраняем..." : "Создать заявку"}</Button>
        </form>
      </Card>
    </AppShell>
  );
}
