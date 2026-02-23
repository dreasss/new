import type { AppProps } from "next/app";
# codex/define-architecture-for-support-system-cphd8w

import ToastViewport from "../components/ui/ToastViewport";
import { ToastProvider } from "../lib/toast";
import "../styles/globals.css";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <ToastProvider>
      <Component {...pageProps} />
      <ToastViewport />
    </ToastProvider>
  );
=======
import "../styles/globals.css";

export default function App({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />;
# main
}
