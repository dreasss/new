import { ReactNode } from "react";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
};

export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  return <button className={`btn btn-${variant} ${className}`.trim()} {...props} />;
}

export function Card({ title, actions, children }: { title?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="card">
      {(title || actions) && (
        <header className="cardHeader">
          {title && <h3>{title}</h3>}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className="input" {...props} />;
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className="textarea" {...props} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className="select" {...props} />;
}

export function Badge({ status }: { status: string }) {
  const key = status.toLowerCase();
  return <span className={`badge badge-${key}`}>{status}</span>;
}

export function PriorityPill({ priority }: { priority: string }) {
  const key = priority.toLowerCase();
  return <span className={`pill pill-${key}`}>{priority}</span>;
}

export function Skeleton({ height = 16 }: { height?: number }) {
  return <div className="skeleton" style={{ height }} aria-hidden="true" />;
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="emptyState">
      <h4>{title}</h4>
      <p>{description}</p>
      {action}
    </div>
  );
}

export function ErrorState({ title, detail, onRetry }: { title: string; detail: string; onRetry: () => void }) {
  return (
    <div className="errorState" role="alert">
      <h4>{title}</h4>
      <p>{detail}</p>
      <Button variant="secondary" onClick={onRetry}>
        Повторить
      </Button>
    </div>
  );
}
