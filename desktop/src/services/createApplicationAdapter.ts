import type { ApplicationAdapter } from "./applicationAdapter";
import { createBrowserAdapter } from "./browserAdapter";
import { createNativeAdapter } from "./nativeAdapter";

export function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export function createApplicationAdapter(): ApplicationAdapter {
  return isTauriRuntime() ? createNativeAdapter() : createBrowserAdapter();
}
