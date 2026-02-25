import { useToast } from "../../lib/toast";

export default function ToastViewport() {
  const { items, remove } = useToast();

  return (
    <div className="toastViewport" aria-live="polite" aria-label="Уведомления">
      {items.map((item) => (
        <div key={item.id} className={`toast toast-${item.kind}`}>
          <span>{item.text}</span>
          <button className="ghostIconButton" onClick={() => remove(item.id)} aria-label="Закрыть уведомление">
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
