use serde::Serialize;
use std::{
    net::TcpListener,
    path::PathBuf,
    sync::Mutex,
};
use tauri::{AppHandle, Manager, State};
use tauri_plugin_shell::{process::CommandChild, ShellExt};
use uuid::Uuid;

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct BackendConnection {
    endpoint: String,
    token: String,
    port: u16,
    pid: Option<u32>,
}

#[derive(Default)]
struct BackendRuntime {
    child: Mutex<Option<CommandChild>>,
    connection: Mutex<Option<BackendConnection>>,
}

#[tauri::command]
fn backend_connection(
    state: State<'_, BackendRuntime>,
) -> Result<BackendConnection, String> {
    state
        .connection
        .lock()
        .map_err(|_| "The backend connection lock is unavailable.".to_string())?
        .clone()
        .ok_or_else(|| "AutoCite's local backend is not running.".to_string())
}

#[tauri::command]
fn restart_backend(
    app: AppHandle,
    state: State<'_, BackendRuntime>,
) -> Result<BackendConnection, String> {
    stop_backend(&state)?;
    start_backend(&app, &state)
}

fn reserve_loopback_port() -> Result<u16, String> {
    let listener = TcpListener::bind(("127.0.0.1", 0))
        .map_err(|error| format!("Could not reserve a local backend port: {error}"))?;
    listener
        .local_addr()
        .map(|address| address.port())
        .map_err(|error| format!("Could not read the local backend port: {error}"))
}

fn session_database(app: &AppHandle) -> Result<PathBuf, String> {
    let directory = app
        .path()
        .app_data_dir()
        .map_err(|error| format!("Could not locate AutoCite's application data: {error}"))?;
    std::fs::create_dir_all(&directory)
        .map_err(|error| format!("Could not create AutoCite's application data directory: {error}"))?;
    Ok(directory.join("sessions.sqlite3"))
}

fn start_backend(
    app: &AppHandle,
    runtime: &BackendRuntime,
) -> Result<BackendConnection, String> {
    let port = reserve_loopback_port()?;
    let token = Uuid::new_v4().simple().to_string();
    let database = session_database(app)?;
    let command = app
        .shell()
        .sidecar("autocite-sidecar")
        .map_err(|error| format!("Could not locate the bundled AutoCite engine: {error}"))?
        .args(["--host", "127.0.0.1", "--port", &port.to_string()])
        .env("AUTOCITE_API_TOKEN", &token)
        .env("AUTOCITE_SESSION_DB", database.as_os_str())
        .env("AUTOCITE_APP_QUIET", "1")
        .env("AUTOCITE_PRINT_TOKEN", "0")
        .env("PYTHONUTF8", "1")
        .env("HF_HUB_OFFLINE", "1")
        .env("TRANSFORMERS_OFFLINE", "1");

    let (mut events, child) = command
        .spawn()
        .map_err(|error| format!("Could not start the bundled AutoCite engine: {error}"))?;

    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
            #[cfg(debug_assertions)]
            match event {
                tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                    eprintln!("AutoCite sidecar: {}", String::from_utf8_lossy(&line));
                }
                tauri_plugin_shell::process::CommandEvent::Error(error) => {
                    eprintln!("AutoCite sidecar error: {error}");
                }
                _ => {}
            }
        }
    });

    {
        let mut child_slot = runtime
            .child
            .lock()
            .map_err(|_| "The backend process lock is unavailable.".to_string())?;
        *child_slot = Some(child);
    }

    let connection = BackendConnection {
        endpoint: format!("http://127.0.0.1:{port}"),
        token,
        port,
        pid: None,
    };
    {
        let mut connection_slot = runtime
            .connection
            .lock()
            .map_err(|_| "The backend connection lock is unavailable.".to_string())?;
        *connection_slot = Some(connection.clone());
    }
    Ok(connection)
}

fn stop_backend(runtime: &BackendRuntime) -> Result<(), String> {
    let child = runtime
        .child
        .lock()
        .map_err(|_| "The backend process lock is unavailable.".to_string())?
        .take();
    if let Some(mut child) = child {
        child
            .kill()
            .map_err(|error| format!("Could not stop the local AutoCite engine: {error}"))?;
    }
    if let Ok(mut connection) = runtime.connection.lock() {
        *connection = None;
    }
    Ok(())
}

fn build_app() -> tauri::App {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            backend_connection,
            restart_backend
        ])
        .setup(|app| {
            let runtime = BackendRuntime::default();
            start_backend(app.handle(), &runtime)
                .map_err(std::io::Error::other)?;
            app.manage(runtime);
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building AutoCite")
}

fn main() {
    let app = build_app();
    app.run(|handle, event| {
        if matches!(event, tauri::RunEvent::Exit) {
            let state = handle.state::<BackendRuntime>();
            let _ = stop_backend(&state);
        }
    });
}
