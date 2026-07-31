use std::{
    fs,
    net::TcpListener,
    path::{Path, PathBuf},
    sync::Mutex,
    time::Duration,
};

use base64::{engine::general_purpose::STANDARD as BASE64, Engine as _};
use reqwest::{Client, Method, StatusCode};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tauri::{Manager, RunEvent, State};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_shell::{process::CommandChild, ShellExt};
use uuid::Uuid;

const MAX_IMPORT_BYTES: u64 = 15 * 1024 * 1024;
const MAX_EXPORT_BYTES: usize = 100 * 1024 * 1024;

struct BackendState {
    base_url: String,
    token: String,
    client: Client,
    child: Mutex<Option<CommandChild>>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct BackendRequest {
    method: String,
    path: String,
    body: Option<Value>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct NativeDocumentFile {
    file_name: String,
    mime_type: Option<String>,
    data_base64: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ExportFile {
    filename: String,
    mime_type: String,
    data_base64: String,
}

fn reserve_loopback_port() -> Result<u16, String> {
    let listener = TcpListener::bind(("127.0.0.1", 0))
        .map_err(|error| format!("could not reserve a loopback port: {error}"))?;
    listener
        .local_addr()
        .map(|address| address.port())
        .map_err(|error| format!("could not read the loopback port: {error}"))
}

fn validate_backend_request(request: &BackendRequest) -> Result<Method, String> {
    if request.path.len() > 2_048
        || !request.path.starts_with("/app")
        || request.path.contains("://")
        || request.path.contains("..")
        || request.path.contains('\0')
        || request.path.contains('\r')
        || request.path.contains('\n')
    {
        return Err("the desktop bridge accepts only local /app paths".to_string());
    }
    match request.method.as_str() {
        "GET" => Ok(Method::GET),
        "POST" => Ok(Method::POST),
        "PATCH" => Ok(Method::PATCH),
        _ => Err("the desktop bridge accepts only GET, POST, and PATCH".to_string()),
    }
}

fn file_name_only(value: &str) -> String {
    Path::new(value)
        .file_name()
        .and_then(|name| name.to_str())
        .filter(|name| !name.trim().is_empty())
        .unwrap_or("autocite-export")
        .chars()
        .filter(|character| !character.is_control())
        .take(180)
        .collect()
}

fn mime_type_for_path(path: &Path) -> Option<String> {
    match path
        .extension()
        .and_then(|extension| extension.to_str())
        .map(str::to_ascii_lowercase)
        .as_deref()
    {
        Some("docx") => Some(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                .to_string(),
        ),
        Some("pdf") => Some("application/pdf".to_string()),
        Some("md" | "markdown") => Some("text/markdown".to_string()),
        Some("txt") => Some("text/plain".to_string()),
        _ => None,
    }
}

fn export_extensions(mime_type: &str, filename: &str) -> Vec<&'static str> {
    if mime_type.contains("wordprocessingml") || filename.ends_with(".docx") {
        vec!["docx"]
    } else if mime_type == "application/pdf" || filename.ends_with(".pdf") {
        vec!["pdf"]
    } else if mime_type.starts_with("text/markdown") || filename.ends_with(".md") {
        vec!["md", "markdown"]
    } else {
        vec!["txt"]
    }
}

#[tauri::command]
async fn backend_request(
    request: BackendRequest,
    state: State<'_, BackendState>,
) -> Result<Value, String> {
    let method = validate_backend_request(&request)?;
    let url = format!("{}{}", state.base_url, request.path);
    let mut last_error = None;

    for attempt in 0..45 {
        let mut builder = state
            .client
            .request(method.clone(), &url)
            .bearer_auth(&state.token)
            .header("cache-control", "no-store");
        if let Some(body) = request.body.as_ref() {
            builder = builder.json(body);
        }
        match builder.send().await {
            Ok(response) => {
                let status = response.status();
                let body = response
                    .json::<Value>()
                    .await
                    .map_err(|error| format!("local backend returned invalid JSON: {error}"))?;
                if status.is_success() {
                    return Ok(body);
                }
                let message = body
                    .get("message")
                    .and_then(Value::as_str)
                    .unwrap_or("local backend request failed");
                return Err(format!("{} {message}", status.as_u16()));
            }
            Err(error) => {
                last_error = Some(error.to_string());
                if attempt < 44 {
                    tokio::time::sleep(Duration::from_millis(80)).await;
                }
            }
        }
    }
    Err(format!(
        "AutoCite's local engine did not become ready: {}",
        last_error.unwrap_or_else(|| "unknown connection failure".to_string())
    ))
}

#[tauri::command]
async fn open_document_file(
    app: tauri::AppHandle,
) -> Result<Option<NativeDocumentFile>, String> {
    let selected = app
        .dialog()
        .file()
        .set_title("Open a document in AutoCite")
        .add_filter("Legal documents", &["docx", "pdf", "md", "markdown", "txt"])
        .blocking_pick_file();
    let Some(selected) = selected else {
        return Ok(None);
    };
    let path = selected
        .into_path()
        .map_err(|error| format!("the selected file is not locally readable: {error}"))?;
    let metadata = fs::metadata(&path)
        .map_err(|error| format!("could not inspect the selected file: {error}"))?;
    if metadata.len() > MAX_IMPORT_BYTES {
        return Err("documents are limited to 15 MB".to_string());
    }
    let bytes = fs::read(&path)
        .map_err(|error| format!("could not read the selected file: {error}"))?;
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| "the selected filename is not valid UTF-8".to_string())?
        .to_string();
    Ok(Some(NativeDocumentFile {
        file_name,
        mime_type: mime_type_for_path(&path),
        data_base64: BASE64.encode(bytes),
    }))
}

#[tauri::command]
async fn save_export_file(
    app: tauri::AppHandle,
    file: ExportFile,
) -> Result<Option<String>, String> {
    if file.data_base64.len() > (MAX_EXPORT_BYTES * 4 / 3) + 8 {
        return Err("the generated export is unexpectedly large".to_string());
    }
    let bytes = BASE64
        .decode(file.data_base64.as_bytes())
        .map_err(|error| format!("the generated export was not valid base64: {error}"))?;
    if bytes.len() > MAX_EXPORT_BYTES {
        return Err("the generated export is unexpectedly large".to_string());
    }
    let filename = file_name_only(&file.filename);
    let extensions = export_extensions(&file.mime_type, &filename);
    let selected = app
        .dialog()
        .file()
        .set_title("Export reviewed document")
        .set_file_name(&filename)
        .add_filter("AutoCite export", &extensions)
        .blocking_save_file();
    let Some(selected) = selected else {
        return Ok(None);
    };
    let path = selected
        .into_path()
        .map_err(|error| format!("the selected export path is not writable: {error}"))?;
    fs::write(&path, bytes)
        .map_err(|error| format!("could not save the exported document: {error}"))?;
    Ok(Some(path.to_string_lossy().into_owned()))
}

fn launch_backend(app: &tauri::App) -> Result<BackendState, String> {
    let port = reserve_loopback_port()?;
    let token = Uuid::new_v4().simple().to_string();
    let app_data_dir = app
        .path()
        .app_data_dir()
        .map_err(|error| format!("could not resolve AutoCite's data directory: {error}"))?;
    fs::create_dir_all(&app_data_dir)
        .map_err(|error| format!("could not create AutoCite's data directory: {error}"))?;
    let database = app_data_dir.join("sessions.sqlite3");

    let command = app
        .shell()
        .sidecar("autocite-backend")
        .map_err(|error| format!("could not prepare the AutoCite sidecar: {error}"))?
        .env("AUTOCITE_API_TOKEN", &token)
        .env("AUTOCITE_HOST", "127.0.0.1")
        .env("AUTOCITE_PORT", port.to_string())
        .env("AUTOCITE_SESSION_DB", database.to_string_lossy().as_ref())
        .env("AUTOCITE_ALLOW_REMOTE", "0")
        .env("AUTOCITE_TRANSPORT", "streamable-http");
    let (mut events, child) = command
        .spawn()
        .map_err(|error| format!("could not launch the AutoCite sidecar: {error}"))?;
    tauri::async_runtime::spawn(async move {
        while events.recv().await.is_some() {
            // Drain sidecar events without forwarding document content to the UI.
        }
    });

    let client = Client::builder()
        .connect_timeout(Duration::from_secs(2))
        .timeout(Duration::from_secs(180))
        .build()
        .map_err(|error| format!("could not initialize the local HTTP client: {error}"))?;
    Ok(BackendState {
        base_url: format!("http://127.0.0.1:{port}"),
        token,
        client,
        child: Mutex::new(Some(child)),
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let state = launch_backend(app).map_err(std::io::Error::other)?;
            app.manage(state);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            backend_request,
            open_document_file,
            save_export_file
        ])
        .build(tauri::generate_context!())
        .expect("error while building AutoCite");

    app.run(|handle, event| {
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            if let Some(state) = handle.try_state::<BackendState>() {
                if let Ok(mut child) = state.child.lock() {
                    if let Some(child) = child.take() {
                        let _ = child.kill();
                    }
                }
            }
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn backend_bridge_allows_only_local_application_paths() {
        let valid = BackendRequest {
            method: "POST".to_string(),
            path: "/app/documents/example/review".to_string(),
            body: None,
        };
        assert_eq!(validate_backend_request(&valid).unwrap(), Method::POST);

        for path in ["https://example.com", "/mcp", "/app/../health", "/app\nhealth"] {
            let invalid = BackendRequest {
                method: "GET".to_string(),
                path: path.to_string(),
                body: None,
            };
            assert!(validate_backend_request(&invalid).is_err());
        }
    }

    #[test]
    fn export_filename_discards_directories_and_controls() {
        assert_eq!(file_name_only("../../Brief\nFinal.docx"), "BriefFinal.docx");
        assert_eq!(file_name_only(""), "autocite-export");
    }

    #[test]
    fn mime_detection_stays_allowlisted() {
        assert_eq!(
            mime_type_for_path(Path::new("brief.DOCX")).as_deref(),
            Some("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        );
        assert!(mime_type_for_path(Path::new("payload.exe")).is_none());
    }

    #[test]
    fn successful_status_constant_remains_available() {
        assert!(StatusCode::OK.is_success());
    }
}
