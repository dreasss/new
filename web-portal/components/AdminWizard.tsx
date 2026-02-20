import { FormEvent, useEffect, useState } from "react";

import { apiGet, apiPost } from "../lib/api";

type Section = "telephony" | "speechkit" | "sso" | "branding" | "phrases";

const sections: Section[] = ["telephony", "speechkit", "sso", "branding", "phrases"];

export default function AdminWizard() {
  const [current, setCurrent] = useState<Section>("telephony");
  const [jsonText, setJsonText] = useState("{}");
  const [alert, setAlert] = useState("");

  async function load(section: Section) {
    const resp = await apiGet(`/api/v1/admin/settings/${section}`);
    if (!resp.ok) {
      setAlert(`Не удалось загрузить секцию ${section}`);
      return;
    }
    const body = await resp.json();
    setJsonText(JSON.stringify(body.config, null, 2));
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
      setAlert("Невалидный JSON");
      return;
    }
    const resp = await apiPost(`/api/v1/admin/settings/${current}`, { config: parsed });
    if (!resp.ok) {
      setAlert(`Ошибка сохранения: ${await resp.text()}`);
      return;
    }
    setAlert(`Секция ${current} сохранена`);
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
      {alert && <p>{alert}</p>}
    </section>
  );
}
