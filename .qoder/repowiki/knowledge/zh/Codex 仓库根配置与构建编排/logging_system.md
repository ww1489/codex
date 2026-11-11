## 1. 使用的框架与工具

Codex 仓库的 Rust 代码统一使用 **tracing** 作为结构化日志/追踪 API，配合 **tracing_subscriber** 完成 subscriber 注册、过滤和输出格式化。关键依赖包括：
- `tracing` — 事件/span API（`tracing::info!` / `warn!` / `error!` 等宏）。
- `tracing_subscriber` — `EnvFilter`、`fmt::layer()`、`Layer` trait、`Registry`、`SubscriberInitExt`。
- `tracing_appender::non_blocking` — 非阻塞异步写入器（TUI 侧）。
- OpenTelemetry 集成通过 `codex_core::otel_init` 提供的 `.logger_layer()` / `.tracing_layer()` / `.metrics()` 注入到 tracing registry。

在 Cargo 层面没有引入其他日志框架（如 `log4rs`、`env_logger`、`simple_logger`、`fern`、`slog`），仅在第三方 vendor 或测试中偶见名称引用，核心二进制均不依赖它们。

## 2. 关键文件与包

| 组件 | 入口/初始化位置 | 职责 |
|---|---|---|
| TUI (`codex-tui`) | `codex-rs/tui/src/lib.rs` | 导入 `tracing_appender::non_blocking`、`tracing_subscriber::EnvFilter`，并构建 subscriber（实际注册逻辑位于同模块后续代码中）；还包含 session 级日志归档 `session_log`。 |
| App Server (`codex-app-server`) | `codex-rs/app-server/src/lib.rs` | 集中式 tracing 初始化：根据 `LOG_FORMAT` 环境变量在 JSON 与默认 human-readable 之间切换，stderr 输出带 span 事件（NEW+CLOSE），并串联 feedback layer、log_db layer 与 OTEL layers。 |
| Exec Server CLI | `codex-rs/exec-server-cli/src/exec_server_telemetry.rs` | 定义默认 filter `"error,opentelemetry_sdk=off,opentelemetry_otlp=off"`，构造 fmt layer → otel tracing layer → otel logger layer 链，并通过 `codex_core::otel_init::build_provider` 启用 metrics。 |
| Windows sandbox | `codex-rs/windows-sandbox-rs/src/logging.rs` | 为 Windows 子进程提供独立的 tracing 初始化。 |
| Core OTEL | `codex-rs/core` 下的 `otel_init` 相关模块 | 封装 OpenTelemetry provider 创建，供上层以 `.logger_layer()` / `.tracing_layer()` / `.metrics()` 接入 tracing。 |
| Log DB | `codex-rs/state/src/log_db.rs` | 将日志事件持久化到 SQLite，暴露 `start(...)` 返回的 layer，并提供 `default_filter()`。 |

## 3. 架构与约定

### 3.1 日志级别控制
- 通过标准 `RUST_LOG` 环境变量驱动 `tracing_subscriber::EnvFilter`（app-server 使用 `EnvFilter::from_default_env()`，exec-server 使用 `try_from_default_env().or_else(try_new(DEFAULT_LOG_FILTER))`）。
- App server 额外通过 `LOG_FORMAT` 环境变量选择输出格式：`json` 时启用 JSON 序列化，否则使用默认 human-readable 格式。
- exec-server 的默认 filter 显式关闭 `opentelemetry_sdk` 和 `opentelemetry_otlp` 的日志，避免重复噪声。

### 3.2 输出目的地
- **stderr**：所有二进制（app-server、exec-server、tui）均以 stderr 为主输出通道。app-server 通过 `codex_app_server_daemon::stderr_writer` 抽象 writer，便于守护进程重定向。
- **SQLite 日志数据库**：app-server 启动时若存在 state_db，则调用 `state::log_db::start(state_db, log_write_warning)` 获得一个额外的 tracing layer，并以 `log_db::default_filter()` 控制写入量。
- **OpenTelemetry**：通过 `codex_core::otel_init` 构建 provider，再将其 `.logger_layer()` 和 `.tracing_layer()` 挂入同一 registry，使 tracing 事件同时进入 OTLP exporter；metrics 单独取出用于 `ExecServerTelemetry`。

### 3.3 Span 行为
- app-server 使用 `FmtSpan::NEW | FmtSpan::CLOSE` 输出 span 的 enter/exit，注释明确说明“preserve span boundaries, busy/idle timings, and explicit events”。
- SQLx 被特别注释跳过其 enter/exit 记录以避免写事务阻塞，但保留显式事件和 span 边界。

### 3.4 多 sink 管线
app-server 的典型 registry 组装顺序（从初始化代码可见）：
```
registry()
  .with(stderr_fmt)            // stderr: json 或 text
  .with(feedback_layer)        // 面向用户的反馈层
  .with(feedback_metadata_layer)
  .with(log_db_layer)          // SQLite 持久化
  .with(otel_layers)           // OTLP exporter
  .try_init()
```
这体现“stderr + 可观测性后端 + 本地持久化”的多 sink 设计。

### 3.5 TUI 的非阻塞写入
TUI 库导入了 `tracing_appender::non_blocking`，表明其采用异步非阻塞 writer 以避免阻塞 UI 渲染线程；具体注册逻辑位于同文件后续部分（搜索 `non_blocking::Builder` 或 `setup_tracing` 可定位）。

## 4. 约定与约束

- **API 层只使用 `tracing` 宏**：代码中广泛使用 `tracing::info!` / `warn!` / `error!` 等结构化字段（如 `event.name = "diagnostic_database_unavailable"`），而非裸 `println!` / `eprintln!`。
- **禁止直接 stdout/stderr 输出**：TUI 与 app-server 均在 crate 根声明 `#![deny(clippy::print_stdout, clippy::print_stderr)]`，强制通过 tracing 输出。
- **日志级别通过环境变量配置**：`RUST_LOG` 是通用过滤器；`LOG_FORMAT=json` 仅对 app-server 生效，用以切换 JSON 输出。
- **OTEL 默认关闭 SDK 自身日志**：exec-server 的默认 filter 显式 `opentelemetry_sdk=off,opentelemetry_otlp=off`，避免日志与遥测数据互相干扰。
- **span 事件策略固定**：app-server 使用 `NEW | CLOSE`，避免频繁 enter/exit 造成 I/O 抖动。
- **结构化字段风格**：使用命名参数形式（如 `%error`、`event.name = ...`）传递结构化字段，而非字符串拼接。
- **日志持久化是可插拔的**：log_db layer 仅在 state_db 可用时挂载，并在不可用时通过 `diagnostic_logs_error()` 上报警告事件，保证降级路径。

这些规则由代码本身（crate-level `deny`、常量、filter 默认值）以及模块内注释共同体现，构成了仓库范围内统一的日志体系。