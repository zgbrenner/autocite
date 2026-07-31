import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";

import { useWorkspace } from "../store/useWorkspace";

export function Toast() {
  const toast = useWorkspace((state) => state.toast);
  const clearToast = useWorkspace((state) => state.clearToast);
  if (!toast) return null;
  return (
    <div className={`toast toast-${toast.tone}`} role={toast.tone === "error" ? "alert" : "status"}>
      <span className="toast-icon">
        {toast.tone === "success" ? <CheckCircle2 /> : toast.tone === "error" || toast.tone === "warning" ? <AlertTriangle /> : <Info />}
      </span>
      <span className="toast-copy"><strong>{toast.title}</strong>{toast.detail ? <small>{toast.detail}</small> : null}</span>
      <button aria-label="Dismiss notification" onClick={clearToast}><X size={15} /></button>
    </div>
  );
}
