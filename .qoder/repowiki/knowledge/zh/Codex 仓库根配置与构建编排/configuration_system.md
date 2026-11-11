## 1. 总体方案

Codex 的配置系统由 Rust crate `codex-rs/config` 实现，采用**分层 TOML + requirements 约束 + 云端企业包**的架构。核心路径是 `codex-rs/config/src/loader/mod.rs` 中的 `load_config_layers_state`，它按固定优先级将多个来源合并成一份最终配置；`requirements_layers/stack.rs` 则对 `requirements.toml` 做领域特定的合并（hooks、rules、permissions、remote_sandbox_config、otel 等）。

- **格式**: 配置文件统一使用 TOML（`config.toml`、`requirements.toml`），默认值内嵌在 `defaults.toml`。
- **类型校验**: 通过 `serde` + `schemars::JsonSchema` + `#[schemars(deny_unknown_fields)]` 进行严格反序列化，未知字段会触发错误。
- **CLI 覆盖**: `--config` 等 CLI 参数通过 `overrides::build_cli_overrides_layer` 作为最高优先级的 session 层注入。
- **线程级配置**: `thread_config/` 提供 per-thread 配置上下文，由 `ThreadConfigLoader` trait 注入。

## 2. 关键文件与模块

| 文件 | 职责 |
|---|---|
| `codex-rs/config/src/lib.rs` | 公共 API 出口，导出 `ConfigLayerSource`、`ConfigLayer`、`ConfigLoadOptions`、`ConfigRequirementsToml` 等类型 |
| `codex-rs/config/src/config_layer_source.rs` | 定义配置来源枚举 `ConfigLayerSource` 及其 precedence 数值 |
| `codex-rs/config/src/loader/mod.rs` | 主加载器 `load_config_layers_state`，编排所有来源 |
| `codex-rs/config/src/loader/local.rs` | 本地 `config.toml` 解析与 `LocalConfigLayers` |
| `codex-rs/config/src/loader/project_discovery.rs` | `.codex/config.toml` 项目发现逻辑 |
| `codex-rs/config/src/loader/managed_requirements.rs` | 从 `/etc/codex/requirements.toml` 与企业云包读取 requirements |
| `codex-rs/config/src/requirements_layers/stack.rs` | requirements 层组合引擎 |
| `codex-rs/config/src/cloud_config_bundle.rs` | 企业云配置包（CloudConfigBundle）的加载与绑定 |
| `codex-rs/config/src/profile_toml.rs` | `ConfigProfile`，用户可选 profile 的结构体定义 |
| `codex-rs/config/src/overrides.rs` | CLI / runtime 覆盖层构建 |
| `codex-rs/config/src/strict_config.rs` | 未知字段检测、忽略字段告警、feature flag 校验 |
| `codex-rs/config/src/schema.rs` | JSON Schema 生成入口 |
| `codex-rs/config/defaults.toml` | 打包客户端内置默认值 |
| `docs/config.md` | 公开配置文档入口（指向外部开发者文档） |

## 3. 配置来源与优先级

`ConfigLayerSource::precedence()` 定义了以下顺序（数值越高越优先）：

1. `PackagedDefaults` (-10) — `defaults.toml` 或构建时注入的 packaged defaults
2. `Mdm` (0) — macOS 设备管理 profile（仅限 macOS）
3. `System` (10) — Unix: `/etc/codex/config.toml`；Windows: `%ProgramData%\OpenAI\Codex\config.toml`
4. `EnterpriseManaged` (15) — 企业云配置包片段
5. `User` (20/21) — `${CODEX_HOME}/config.toml`；带 profile 时为 21
6. `Project` (25) — 当前工作目录到根查找 `.codex/config.toml`，以及 git repo 根目录的 `.codex/config.toml`（在未受信任目录中会被加载但禁用）
7. `SessionFlags` (30) — CLI `--config` 等运行时覆盖
8. `LegacyManagedConfigTomlFromFile` (40) — 向后兼容的 `/etc/codex/managed_config.toml`
9. `LegacyManagedConfigTomlFromMdm` (50) — 来自 MDM 的 legacy managed config

requirements 层也遵循相同顺序：package → admin(managed preferences) → system `/etc/codex/requirements.toml` → cloud enterprise bundle → user → project/session。

## 4. 设计约定与约束

- **TOML 结构强类型化**: 每个配置子域（model provider、browser use、computer use、mcp、skills、tui、hooks 等）都有独立的 `*Toml` 结构体，普遍使用 `#[schemars(deny_unknown_fields)]` 禁止未知字段。
- **project-local 配置黑名单**: `loader/mod.rs` 中的 `PROJECT_LOCAL_CONFIG_DENYLIST` 显式禁止在项目级配置中设置敏感字段（如 `openai_base_url`、`chatgpt_base_url`、`model_provider`、`notify`、`profile`、`otel` 等），这些只能出现在 user/system/managed/runtime 层。
- **安全与信任模型**: 项目级 `.codex/config.toml` 会根据 `project_trust` 机制被“加载但禁用”，防止不受信任代码篡改凭证存储位置或本地命令。
- **Requirements 特殊合并语义**: 并非简单 TOML 替换。`requirements_layers/stack.rs` 为 `remote_sandbox_config`、`rules.prefix_rules`、`hooks`、`permissions.filesystem.deny_read`、`auto_review.required_on_models`、`otel` 等字段实现了领域特定的合并策略（append、union、atomic replace 等）。
- **Profile 支持**: 用户可通过 `profile_toml.rs` 定义的 `ConfigProfile` 选择命名配置单元，profile 的 precedence 高于普通 user 配置。
- **云端企业配置**: `cloud_config_bundle.rs` 加载远程下发的 bundle，将其拆分为 `enterprise_managed_config`（config 层）和 `enterprise_managed_requirements`（requirements 层），并与本地层合并。
- **诊断与溯源**: 每个 `ConfigLayer` 附带 `ConfigLayerSource`、version、disabled_reason，配合 `diagnostics.rs` 输出可审计的配置生效链。
- **JSON Schema 生成**: `schema.rs` 基于 schemars 为所有配置结构生成 JSON Schema，供 IDE 提示和验证使用。
- **默认值内嵌**: `defaults.toml` 通过 `include_str!` 嵌入二进制，避免依赖运行时文件；也可通过 `overrides.packaged_defaults_path` 指定替代文件。

## 5. 与其他组件的关系

- CLI (`codex-rs/cli`) 通过 `ConfigLoadOptions` 传入 `--config`、`--profile`、`--ignore-user-config`、`--ignore-project-config` 等选项。
- TUI (`codex-rs/tui`) 消费最终配置驱动 UI 行为。
- App Server (`codex-rs/app-server`) 通过线程无关加载（cwd=None）暴露 `/config` 端点。
- Sandbox、exec-server、MCP、hooks、skills 等子系统各自定义自己的 `*Toml` 结构体，由 `config` crate 统一加载与合并。

## 6. 观察到的规则（来源于代码强制）

- 未知 TOML 字段导致反序列化失败（`deny_unknown_fields` 注解）。
- 项目级配置中若出现 `PROJECT_LOCAL_CONFIG_DENYLIST` 中的键，会被拒绝。
- 未受信任目录中的 `.codex/config.toml` 虽被加载，但整个 layer 被标记为 disabled。
- legacy `managed_config.toml` 仍被向后兼容地映射为 `requirements.toml`，并赋予最高 precedence (40/50)。
- macOS 上仅允许通过 MDM 注入 `Mdm` 层（条件编译 `#[cfg(target_os = "macos")]`）。
