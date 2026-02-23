# codex/define-architecture-for-support-system-cphd8w
import { useEffect, useState } from "react";

import { ApiError, getAdminSetting, saveAdminSetting } from "../lib/api";
import { useToast } from "../lib/toast";
import { Button, Card, ErrorState, Input, Textarea } from "./ui/primitives";

type Section = "branding" | "phrases" | "telephony" | "speechkit" | "sso";

const sections: Array<{ key: Section; label: string }> = [
  { key: "branding", label: "Брендинг" },
  { key: "phrases", label: "Фразы бота" },
  { key: "telephony", label: "Телефония" },
  { key: "speechkit", label: "SpeechKit" },
  { key: "sso", label: "SSO" },
];

export default function AdminWizard() {
  const { push } = useToast();
  const [current, setCurrent] = useState<Section>("branding");
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function load(section: Section) {
    setLoading(true);
    setError("");
    try {
      const body = await getAdminSetting(section);
      setConfig(body.config || {});
    } catch (err) {
      const e = err as ApiError;
      setError(e.message || "Ошибка загрузки настроек");
    } finally {
      setLoading(false);
    }
=======
import { FormEvent, useEffect, useState } from "react";

import { apiGet, apiPost } from "../lib/api";

type Section = "telephony" | "speechkit" | "sso" | "branding" | "phrases";
# codex/define-architecture-for-support-system-j19u82
type AlertKind = "success" | "error";

=======
# codex/define-architecture-for-support-system-e3u2rv
type AlertKind = "success" | "error";

# main

# main
const sections: Section[] = ["telephony", "speechkit", "sso", "branding", "phrases"];

export default function AdminWizard() {
  const [current, setCurrent] = useState<Section>("telephony");
  const [jsonText, setJsonText] = useState("{}");
# codex/define-architecture-for-support-system-j19u82
  const [alert, setAlert] = useState<{ kind: AlertKind; text: string } | null>(null);

  async function load(section: Section) {
    const resp = await apiGet(`/api/v1/admin/settings/${section}`);
    if (!resp.ok) {
      setAlert({ kind: "error", text: `Не удалось загрузить секцию ${section}: ${await resp.text()}` });
=======
# codex/define-architecture-for-support-system-e3u2rv
  const [alert, setAlert] = useState<{ kind: AlertKind; text: string } | null>(null);

  const [alert, setAlert] = useState("");
# main

  async function load(section: Section) {
    const resp = await apiGet(`/api/v1/admin/settings/${section}`);
    if (!resp.ok) {
# codex/define-architecture-for-support-system-e3u2rv
      setAlert({ kind: "error", text: `Не удалось загрузить секцию ${section}: ${await resp.text()}` });

      setAlert(`Не удалось загрузить секцию ${section}`);
# main
# main
      return;
    }
    const body = await resp.json();
    setJsonText(JSON.stringify(body.config, null, 2));
# codex/define-architecture-for-support-system-j19u82
    setAlert(null);
=======
# codex/define-architecture-for-support-system-e3u2rv
    setAlert(null);

# main
# main

  }

  useEffect(() => {
    load(current);
  }, [current]);

# codex/define-architecture-for-support-system-cphd8w
  async function save() {
    setSaving(true);
    try {
      const body = await saveAdminSetting(current, config);
      setConfig(body.config || {});
      push("success", `Секция ${current} сохранена`);
    } catch (err) {
      const e = err as ApiError;
      push("error", `Ошибка сохранения: ${e.message}`);
    } finally {
      setSaving(false);
    }
  }

  function updateField(key: string, value: unknown) {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <Card title="Admin Wizard">
      <div className="stepper">
        {sections.map((s, idx) => (
          <button key={s.key} className={current === s.key ? "step active" : "step"} onClick={() => setCurrent(s.key)}>
            {idx + 1}. {s.label}
          </button>
        ))}
      </div>

      {loading && <p className="muted">Загрузка секции...</p>}
      {!loading && error && <ErrorState title="Ошибка секции" detail={error} onRetry={() => load(current)} />}

      {!loading && !error && (
        <div className="formGrid">
          {current === "branding" && (
            <>
              <label>Название портала</label>
              <Input
                value={String(config.title ?? "")}
                onChange={(e) => updateField("title", e.target.value)}
                placeholder="Support Portal"
              />
              <label>Основной цвет</label>
              <Input
                value={String(config.primaryColor ?? "")}
                onChange={(e) => updateField("primaryColor", e.target.value)}
                placeholder="#2F6BFF"
              />
              <label>Логотип URL</label>
              <Input value={String(config.logoUrl ?? "")} onChange={(e) => updateField("logoUrl", e.target.value)} />
            </>
          )}

          {current === "phrases" && (
            <>
              <label>Greeting</label>
              <Textarea
                rows={3}
                value={String(config.greeting ?? "Здравствуйте! Это служба поддержки.")}
                onChange={(e) => updateField("greeting", e.target.value)}
              />
              <label>Incomplete message</label>
              <Textarea
                rows={3}
                value={String(config.incomplete ?? "Недостаточно данных, подключаем оператора.")}
                onChange={(e) => updateField("incomplete", e.target.value)}
              />
            </>
          )}

          {current === "telephony" && (
            <>
              <label>DID</label>
              <Input value={String(config.did ?? "")} onChange={(e) => updateField("did", e.target.value)} />
              <label>handoff_on_incomplete</label>
              <select
                className="select"
                value={String(config.handoff_on_incomplete ?? false)}
                onChange={(e) => updateField("handoff_on_incomplete", e.target.value === "true")}
              >
                <option value="false">false</option>
                <option value="true">true</option>
              </select>
            </>
          )}

          {current === "speechkit" && (
            <>
              <label>voice</label>
              <Input value={String(config.voice ?? "ermil")} onChange={(e) => updateField("voice", e.target.value)} />
              <label>speed</label>
              <Input value={String(config.speed ?? "1.0")} onChange={(e) => updateField("speed", Number(e.target.value))} />
              <label>volume</label>
              <Input value={String(config.volume ?? "0")} onChange={(e) => updateField("volume", Number(e.target.value))} />
            </>
          )}

          {current === "sso" && (
            <>
              <label>provider</label>
              <Input value={String(config.provider ?? "OIDC")} onChange={(e) => updateField("provider", e.target.value)} />
              <label>issuer / metadata URL</label>
              <Input value={String(config.issuer ?? "")} onChange={(e) => updateField("issuer", e.target.value)} />
            </>
          )}

          <div className="inlineActions">
            <Button onClick={save} disabled={saving}>
              {saving ? "Сохраняем..." : "Сохранить и применить"}
            </Button>
          </div>
        </div>
      )}
    </Card>
=======
  async function save(e: FormEvent) {
    e.preventDefault();
    let parsed;
    try {
      parsed = JSON.parse(jsonText);
    } catch {
# codex/define-architecture-for-support-system-j19u82
      setAlert({ kind: "error", text: "Невалидный JSON" });
=======
# codex/define-architecture-for-support-system-e3u2rv
      setAlert({ kind: "error", text: "Невалидный JSON" });

      setAlert("Невалидный JSON");
# main
# main
      return;
    }
    const resp = await apiPost(`/api/v1/admin/settings/${current}`, { config: parsed });
    if (!resp.ok) {
# codex/define-architecture-for-support-system-j19u82
=======
# codex/define-architecture-for-support-system-e3u2rv
# main
      setAlert({ kind: "error", text: `Ошибка сохранения: ${await resp.text()}` });
      return;
    }
    const body = await resp.json();
    setJsonText(JSON.stringify(body.config, null, 2));
    setAlert({ kind: "success", text: `Секция ${current} сохранена` });
# codex/define-architecture-for-support-system-j19u82
=======

      setAlert(`Ошибка сохранения: ${await resp.text()}`);
      return;
    }
    setAlert(`Секция ${current} сохранена`);
# main
# main
  }

  return (
    <section>
      <h2>Admin wizard</h2>
      <div>
        {sections.map((s) => (
          <button key={s} onClick={() => setCurrent(s)}>
            {s}
          </button>
        ))}
      </div>
      <form onSubmit={save}>
        <h3>{current}</h3>
        <textarea value={jsonText} onChange={(e) => setJsonText(e.target.value)} rows={14} cols={80} />
        <br />
        <button type="submit">Сохранить</button>
      </form>
# codex/define-architecture-for-support-system-j19u82
      {alert && <p style={{ color: alert.kind === "error" ? "#dc2626" : "#15803d" }}>{alert.text}</p>}
=======
# codex/define-architecture-for-support-system-e3u2rv
      {alert && <p style={{ color: alert.kind === "error" ? "#dc2626" : "#15803d" }}>{alert.text}</p>}

      {alert && <p>{alert}</p>}
# main
# main
    </section>
# main
  );
}
