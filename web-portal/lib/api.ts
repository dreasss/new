# codex/define-architecture-for-support-system-cphd8w
export const API = process.env.NEXT_PUBLIC_CORE_API_URL || "http://localhost:8000";

export type ApiError = {
  status: number;
  message: string;
};

export type Me = {
  id: number;
  email: string;
  role: "user" | "support" | "admin";
};

export type Ticket = {
  id: number;
  subject: string;
  description: string;
  status: string;
  channel: string;
  assigned_user_id: number | null;
  created_by_user_id: number;
  created_at?: string;
  updated_at?: string;
};

export type CommentItem = {
  id: number;
  author_user_id: number;
  content: string;
  created_at?: string;
};

export type HistoryItem = {
  id: number;
  event_type: string;
  from_status?: string | null;
  to_status?: string | null;
  message?: string | null;
  created_at?: string;
  correlation_id?: string | null;
};

export type SystemSettingResponse = {
  section: string;
  config: Record<string, unknown>;
};

function tokenHeader(): HeadersInit {
=======
export const API = process.env.NEXT_PUBLIC_CORE_API_URL;

export function tokenHeader(): HeadersInit {
# main
  const token = typeof window === "undefined" ? null : localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

# codex/define-architecture-for-support-system-cphd8w
async function parseResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!response.ok) {
    throw {
      status: response.status,
      message: text || response.statusText,
    } as ApiError;
  }
  return text ? (JSON.parse(text) as T) : ({} as T);
}

export async function apiGet<T>(path: string, extraHeaders?: HeadersInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    headers: {
      ...tokenHeader(),
      ...extraHeaders,
    },
  });
  return parseResponse<T>(response);
}

export async function apiPost<T>(path: string, body: unknown, extraHeaders?: HeadersInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...tokenHeader(),
      ...extraHeaders,
    },
    body: JSON.stringify(body),
  });
  return parseResponse<T>(response);
}

export async function login(email: string, password: string): Promise<{ access_token: string }> {
  return apiPost<{ access_token: string }>("/api/v1/auth/login", { email, password });
}

export async function fetchMe(): Promise<Me> {
  return apiGet<Me>("/api/v1/auth/me");
}

export async function fetchMyTickets(params?: {
  status?: string;
  channel?: string;
  search?: string;
}): Promise<{ items: Ticket[] }> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.channel) qs.set("channel", params.channel);
  if (params?.search) qs.set("q", params.search);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiGet<{ items: Ticket[] }>(`/api/v1/tickets${suffix}`);
}

export async function fetchSupportTickets(params?: {
  status_filter?: string;
  channel?: string;
  search?: string;
}): Promise<{ items: Ticket[] }> {
  const qs = new URLSearchParams();
  if (params?.status_filter) qs.set("status_filter", params.status_filter);
  if (params?.channel) qs.set("channel", params.channel);
  if (params?.search) qs.set("q", params.search);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiGet<{ items: Ticket[] }>(`/api/v1/support/tickets${suffix}`);
}

export async function fetchTicket(ticketId: string): Promise<Ticket> {
  return apiGet<Ticket>(`/api/v1/tickets/${ticketId}`);
}

export async function fetchTicketComments(ticketId: string): Promise<{ items: CommentItem[] }> {
  return apiGet<{ items: CommentItem[] }>(`/api/v1/tickets/${ticketId}/comments`);
}

export async function fetchTicketHistory(ticketId: string): Promise<HistoryItem[]> {
  return apiGet<HistoryItem[]>(`/api/v1/tickets/${ticketId}/history`);
}

export async function createTicket(body: {
  subject: string;
  description: string;
  channel: "web" | "voice";
}): Promise<Ticket> {
  return apiPost<Ticket>("/api/v1/tickets", body);
}

export async function addTicketComment(ticketId: string, content: string): Promise<{ id: number }> {
  return apiPost<{ id: number }>(`/api/v1/tickets/${ticketId}/comments`, { content });
}

export async function closeTicket(ticketId: string, resolution_comment: string): Promise<{ id: number }> {
  return apiPost<{ id: number }>(`/api/v1/tickets/${ticketId}/close`, { resolution_comment });
}

export async function rateTicket(ticketId: string, score: number, comment: string): Promise<{ id: number }> {
  return apiPost<{ id: number }>(`/api/v1/tickets/${ticketId}/ratings`, { score, comment });
}

export async function assignSelf(ticketId: number): Promise<{ id: number }> {
  return apiPost<{ id: number }>(`/api/v1/tickets/${ticketId}/assign-self`, {});
}

export async function setTicketStatus(ticketId: number, status: string): Promise<{ id: number }> {
  return apiPost<{ id: number }>(`/api/v1/tickets/${ticketId}/status`, { status });
}

export async function getAdminSetting(section: string): Promise<SystemSettingResponse> {
  return apiGet<SystemSettingResponse>(`/api/v1/admin/settings/${section}`);
}

export async function saveAdminSetting(section: string, config: Record<string, unknown>): Promise<SystemSettingResponse> {
  return apiPost<SystemSettingResponse>(`/api/v1/admin/settings/${section}`, { config });
}

export async function fetchBranding(): Promise<{ config: Record<string, unknown> }> {
  return apiGet<{ config: Record<string, unknown> }>("/api/v1/public/branding");
=======
export async function apiGet(path: string) {
  return fetch(`${API}${path}`, { headers: { ...tokenHeader() } });
}

export async function apiPost(path: string, body: unknown, extraHeaders?: HeadersInit) {
  return fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...tokenHeader(), ...extraHeaders },
    body: JSON.stringify(body),
  });
# main
}
