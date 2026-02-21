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
  );
}
