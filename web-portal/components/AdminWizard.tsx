import { useEffect, useState } from "react";

import { apiGet, apiPost, ApiError, SystemSettingResponse } from "../lib/api";
import { Button, Card, ErrorState, Input, Textarea } from "./ui/primitives";

type Section = "branding" | "phrases" | "telephony" | "speechkit" | "sso";
type AlertKind = "success" | "error";

const sections: Array<{ key: Section; label: string }> = [
  { key: "branding", label: "Брендинг" },
  { key: "phrases", label: "Фразы бота" },
  { key: "telephony", label: "Телефония" },
  { key: "speechkit", label: "SpeechKit" },
  { key: "sso", label: "SSO" },
];

export default function AdminWizard() {
  const [current, setCurrent] = useState<Section>("branding");
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [alert, setAlert] = useState<{ kind: AlertKind; text: string } | null>(null);

  async function load(section: Section) {
    setLoading(true);
    try {
      const body = await apiGet<SystemSettingResponse>(`/api/v1/admin/settings/${section}`);
      setConfig(body.config ?? {});
      setAlert(null);
    } catch (err) {
      const e = err as ApiError;
      const msg = e.message || "unknown error";
      setAlert({ kind: "error", text: `Не удалось загрузить секцию ${section}: ${msg}` });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(current);
  }, [current]);

  async function save() {
    setSaving(true);
    try {
      const body = await apiPost<SystemSettingResponse>(`/api/v1/admin/settings/${current}`, { config });
      setConfig(body.config ?? {});
      setAlert({ kind: "success", text: `Секция ${current} сохранена` });
    } catch (err) {
      const e = err as ApiError;
      const msg = e.message || "unknown error";
      setAlert({ kind: "error", text: `Ошибка сохранения: ${msg}` });
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
      {!loading && alert?.kind === "error" && <ErrorState title="Ошибка секции" detail={alert.text} onRetry={() => load(current)} />}

      {!loading && (!alert || alert.kind !== "error") && (
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
            {alert?.kind === "success" && <p className="muted">{alert.text}</p>}
          </div>
        </div>
      )}
    </Card>
  );
}
