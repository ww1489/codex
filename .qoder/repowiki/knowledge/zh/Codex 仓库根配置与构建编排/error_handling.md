## 1. 总体方案

Codex 的 Rust 代码库（`codex-rs/`）统一使用 **Rust 原生 `std::error::Error` + `thiserror::Error`** 定义错误类型，不引入 `anyhow`、`eyre` 等通用包装器作为 API 边界。核心策略是：

- 每个领域模块定义自己的 `enum Error` / `struct Error`（例如 `execpolicy::Error`、`SandboxErr`），通过 `#[derive(Error)]` 提供 `Display`。
- 顶层协议层 `codex-protocol/src/error.rs` 暴露一个统一的 `CodexErr` 包裹类型，内部持有语义分类 `CodexErrorDetails` 枚举，以及可选的 `RetryAfter` 和 `AgentErrorContext`。
- 调用链中广泛使用 `From<T>` 将底层错误自动提升为 `CodexErr`，对外只暴露 `CodexErr`。

## 2. 关键文件与包

| 文件 | 作用 |
|---|---|
| `codex-rs/protocol/src/error.rs` | 全局错误中心：`CodexErr`、`CodexErrorDetails`、`SandboxErr`、`UnexpectedResponseError`、`ConnectionFailedError`、`ResponseStreamFailed`、`RetryLimitReachedError`、`UsageLimitReachedError`、`ProviderRejection` 等 |
| `codex-rs/protocol/src/agent_error.rs` | `AgentErrorContext`（被 `CodexErr` 携带，用于把 agent 上下文附加到错误上） |
| `codex-rs/execpolicy/src/error.rs` | exec-policy 专用错误（含 `TextPosition`/`TextRange`/`ErrorLocation` 源码定位辅助） |
| `codex-rs/cli/src/main.rs` | CLI 入口，负责把应用退出信息（`ExitReason`、`AppExitInfo`）格式化输出并决定是否以状态码 1 退出 |
| `codex-rs/tui/src/...` | TUI 层消费 `CodexErrorInfo`（来自 `app-server-protocol`）进行展示 |

## 3. 架构与约定

### 3.1 分层错误模型

`CodexErr` 由三层组成：

```
CodexErr
├── details: CodexErrorDetails   ← 语义分类（用户可见的错误类别）
├── retry_after: Option<RetryAfter> ← 服务器建议的重试时间
└── agent_context: Option<AgentErrorContext> ← agent 诊断上下文
```

`CodexErrorDetails` 是一个大型枚举，包含约 60+ 个变体，如 `TurnAborted`、`SessionBudgetExceeded`、`RateLimitExceeded(String)`、`ContentFilter`、`ContextWindowExceeded`、`ModelNotFound { message, status }`、`InvalidPrompt { message }`、`InferenceHookDenied { message }`、`ContentPolicyViolation { message, status }`、`CyberPolicy/BioPolicy/MisalignmentPolicyViolation`、`ServerOverloaded`、`PolicyCapacityUnavailable`、`FlexUnavailable`、`QuotaExceeded`、`UsageNotIncluded`、`InternalAgentDied`、`Sandbox(SandboxErr)`、`RefreshTokenFailed(...)`、`GatewayLoginRequired(...)`、`Fatal(String)` 等。所有变体都通过 `#[error("...")]` 声明人类可读消息。

`SandboxErr` 是独立子枚举，封装沙箱执行失败（`Denied`、`Timeout`、`Signal`、`LandlockRestrict` 及 Linux seccomp 错误）。

### 3.2 自动转换与 `From` 实现

`CodexErr` 对常见外部错误实现了 `From`，使它们可以自动提升到顶层：

- `io::Error` → `Io`
- `serde_json::Error` → `Json`
- `tokio::task::JoinError` → `TokioJoin`
- `landlock::RulesetError` / `PathFdError`（Linux）→ `LandlockRuleset` / `LandlockPathFd`
- `CancelErr` → `TurnAborted`
- `SandboxErr` → `Sandbox`

这些转换全部在 `protocol/src/error.rs` 集中声明，保证所有上游模块只需返回更具体的错误类型，即可被下游消费。

### 3.3 可重试性判定

`CodexErr::retry_delay(retry_count: u64) -> Option<Duration>` 是重试决策的核心：

- **不可重试（返回 `None`）**：`TurnAborted`、`SessionBudgetExceeded`、`Interrupted`、`EnvVar`、`Fatal`、`UsageNotIncluded`、`QuotaExceeded`、`InvalidImageRequest`、`InvalidRequest`、`InvalidAudioInput`、`ResponseIncomplete`、`ModelNotFound`、`InvalidPrompt`、`InferenceHookDenied`、`ContentPolicyViolation`、`ToolCollision`、`RefreshTokenFailed`、`GatewayLoginRequired`、`UnsupportedOperation`、`Sandbox`、`LandlockSandboxExecutableNotProvided`、`ContextWindowExceeded`、`ThreadNotFound`、`AgentLimitReached`、`Spawn`、`SessionConfiguredNotFirstEvent`、`UsageLimitReached`、`FlexUnavailable`、`CyberPolicy`、`BioPolicy`、`WorkspaceAccessDenied`、`AccessProgramNotEnabled`、`MisalignmentPolicyViolation`、`LandlockRuleset`、`LandlockPathFd`。
- **可重试（返回延迟）**：`ServerOverloaded`、`PolicyCapacityUnavailable`、`RetryLimit`、`Stream`、`ContentFilter`、`RateLimitExceeded`、`Timeout`、`RequestTimeout`、`UnexpectedStatus`、`ResponseStreamFailed`、`ConnectionFailed`、`InternalServerError`、`InternalAgentDied`、`Io`、`Json`、`TokioJoin`。
- 可重试错误优先使用 `server_retry_delay()`（即 `RetryAfter.remaining_delay`），否则回退到 `backoff(retry_count)` 指数退避。

`is_runtime_auth_denial(status, body, identity_error_code)` 单独判断“运行时身份拒绝”是否属于不可修复的终止错误（检查特定 `identity_error_code` 值或 JSON body 中的 `/error/code`）。

### 3.4 协议映射与 UI 展示

`to_codex_protocol_error(&self) -> CodexErrorInfo` 将内部语义分类映射到客户端协议枚举（`ContextWindowExceeded`、`RateLimitExceeded`、`UsageLimitExceeded`、`ServerOverloaded`、`PolicyCapacityUnavailable`、`FlexUnavailable`、`InferenceHookDenied`、`CyberPolicy`、`BioPolicy`、`ModelNotFound`、`InvalidPrompt`、`MisalignmentPolicyViolation`、`HttpConnectionFailed`、`ResponseStreamConnectionFailed`、`Unauthorized`、`InternalServerError`、`BadRequest`、`SandboxError`、`Other`）。该函数还附带 `http_status_code_value()` 提取原始 HTTP 状态码。

`to_error_event(message_prefix)` 生成 TUI 显示的 `ErrorEvent`，消息上限为 `ERROR_MESSAGE_UI_MAX_BYTES = 2 * 1024`。

`UnexpectedResponseError` 负责解析非预期 HTTP 响应体，优先取结构化 `error.message`，否则拼接 `{status}: {body}`，并截断至 `UNEXPECTED_RESPONSE_BODY_MAX_BYTES = 1000` 字节。

### 3.5 CLI 退出行为

CLI 入口 (`cli/src/main.rs`) 不直接读取 `CodexErr` 来决定退出码；它接收 `AppExitInfo`（含 `ExitReason`、`UpdateAction`、格式化后的退出消息列表），仅当 `ExitReason::Fatal` 时 `std::process::exit(1)`，其他情况正常返回（成功退出码 0）。

### 3.6 其他模块的错误模式

- `execpolicy::Error`：基于 thiserror 的领域错误，额外提供 `with_location(ErrorLocation)` 和 `location()` 方法，从 Starlark 错误中提取源码位置（行/列）。
- 各子模块普遍采用 `pub type Result<T> = std::result::Result<T, Error>` 的命名约定。
- 不使用 `panic!` 作为错误传播手段——错误通过 `Result` 向上冒泡。

## 4. 约定与约束

- **错误类型必须使用 `#[derive(Error)]` + `#[error("...")]`**：仓库内所有自定义错误均遵循此模式（见 `protocol/src/error.rs`、`execpolicy/src/error.rs` 及各模块 error 文件），这是 by observation 的统一惯例。
- **对外 API 边界统一收敛于 `CodexErr`**：`protocol/src/error.rs` 集中实现 `From<T>` 将所有常见外部错误提升为 `CodexErr`，下游无需处理裸 `io::Error`、`serde_json::Error`、`JoinError` 等。
- **可重试性判定集中在 `retry_delay`**：新增错误变体时必须在此函数中添加分支，决定其是否可重试；这是唯一控制重试逻辑的位置。
- **协议映射集中在 `to_codex_protocol_error`**：新增面向客户端的错误类别时，应在此处添加对应映射，确保 TUI/SDK 能识别。
- **用户可见消息限制大小**：UI 侧错误消息被裁剪到 2 KiB（`ERROR_MESSAGE_UI_MAX_BYTES`），HTTP 响应体裁剪到 1 KiB（`UNEXPECTED_RESPONSE_BODY_MAX_BYTES`）。
- **CLI 不直接使用 `CodexErrKind` 做退出码判断**：CLI 通过 `AppExitInfo`/`ExitReason` 表达最终结果，而非根据错误语义分类设置不同 exit code；只有 `Fatal` 才会显式返回 1。
- **`downcast_ref::<T>` 兼容 shim**：`CodexErr` 提供了 `downcast_ref` 方法以兼容历史代码中对 `anyhow::Error` 的 downcast 习惯，但新代码应直接匹配 `CodexErrorDetails` 变体。

## 5. 适用性说明

本仓库是一个大型 Rust monorepo，错误处理是跨所有子模块（`core`、`tui`、`cli`、`sandboxing`、`login`、`cloud-client`、`windows-sandbox-*` 等）的基础设施，具有明确的中心类型、集中式可重试性/协议映射逻辑，因此本类别完全适用且证据充分。