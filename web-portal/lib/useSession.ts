import { useRouter } from "next/router";
import { useCallback, useEffect, useState } from "react";

import { ApiError, fetchMe, Me } from "./api";

export function useSession(required = true) {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchMe();
      setMe(data);
    } catch (err) {
      const e = err as ApiError;
      setError(e.message || "Ошибка сессии");
      if (required && e.status === 401) {
        localStorage.removeItem("token");
        router.replace("/");
      }
    } finally {
      setLoading(false);
    }
  }, [required, router]);

  useEffect(() => {
    load();
  }, [load]);

  return { me, loading, error, reload: load };
}
