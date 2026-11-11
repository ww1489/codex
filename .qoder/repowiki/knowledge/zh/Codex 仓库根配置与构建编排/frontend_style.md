## 概述

本仓库的「前端」是 Rust 编写的 TUI（基于 [ratatui](https://github.com/ratatui-org/ratatui)），以及一个用于 Agent 侧 Markdown/HTML 内联渲染的浏览器端 CSS。两者共同构成 Codex 的视觉风格体系，分别覆盖终端 UI 和 Web 内联可视化两类界面。

## 1. 终端 UI（TUI）样式系统

### 核心文件
- `codex-rs/tui/src/style.rs` — 共享的颜色常量、语义样式函数（`status_style`、`accent_style`、`secondary_text_style`、`user_message_style`、`shortcut_hud_style`、`history_prompt_style`、`task_marker` 等），通过 `terminal_palette` 根据终端能力（ANSI 16 / 256 / TrueColor）选择颜色。
- `codex-rs/tui/styles.md` — 样式规范文档，明确字体粗细、前景色使用规则、键盘提示符、菜单描述等约定。
- `codex-rs/tui/src/theme_picker.rs` — `/theme` 选择器对话框，支持 `.tmTheme` 语法高亮主题切换与持久化到 `[tui] theme = ...`。
- `codex-rs/tui/src/ui_tree/theme.rs`、`codex-rs/tui/src/render/model_themes.rs` — 主题模型与 Mermaid 样式跟随主题的快照测试。
- `codex-rs/tui/src/terminal_palette.rs`（由 style.rs 导入）— 检测终端色彩能力并返回 RGB/ANSI 颜色。

### 架构与约定
- **语义优先**：不直接使用裸 ANSI 色值，而是调用 `style::status_style(StatusTone)`、`style::accent_style()`、`style::secondary_text_style()` 等封装函数，内部再按终端色深降级回 `Color::Reset`。
- **对比度保障**：`style::readable_color_on(color, background)` 在未知背景时保留主题色，已知背景时做对比度检查；禁止“未检查的自定义前景色”。
- **主题来源**：内置主题 + `{CODEX_HOME}/themes/*.tmTheme` 自定义主题，用户可通过 `/theme` 命令实时预览并写入配置。
- **状态语义**：Success → ANSI green，Failure → ANSI red，Attention → 仅在已知深色背景时用 Yellow，否则回退 Reset。
- **禁用色**：明确避免 ANSI black/white/blue/yellow 作为普通前景色（styles.md 规定），蓝色/黄色不在当前风格指南中。
- **Clippy 约束**：styles.md 末尾声明“有一些 clippy 规则试图捕获此行为”，对应根级 `clippy.toml` 中的 lint（具体条目见仓库）。 

### 关键文件
- `codex-rs/tui/src/style.rs`
- `codex-rs/tui/styles.md`
- `codex-rs/tui/src/theme_picker.rs`
- `codex-rs/tui/src/ui_tree/theme.rs`
- `codex-rs/tui/src/render/model_themes.rs`

## 2. 浏览器端内联可视化样式

### 核心文件
- `codex-rs/tui/assets/inline_visualization/visualize.css` — 完整的 CSS 变量主题系统，定义 `:root` 下的 design tokens（`--background`、`--foreground`、`--primary`、`--accent`、`--destructive`、`--border`、`--ring`、字号阶梯、圆角、阴影、系列色 `--viz-series-*` 等），并通过 `light-dark(...)` 原生 CSS 函数同时提供明暗两套值。

### 架构与约定
- **CSS 变量设计令牌**：所有颜色、字号、圆角、阴影均通过 `var(--*)` 暴露给消费方（Agent 生成的 HTML/SVG 图表）。注释明确标注哪些是“Agent-facing contract”（需与 SKILL.md 同步）、哪些是“internal implementation variables”。
- **明暗主题**：通过 `data-theme="light"|"dark"` 或 `color-scheme: light dark` 自动切换；旧别名 `--color-background-primary` 等保留兼容性。
- **字体栈**：`--font-sans` 使用 `-apple-system-body, ui-sans-serif, system-ui, Segoe UI...`，`--font-mono` 使用 SF Mono/Menlo/Liberation Mono。
- **可定制性**：宿主可在 `<html>` 上覆盖 `--color-background-primary`、`--color-text-primary`、`--color-border-secondary` 等变量以适配自身主题。
- **无外部框架**：该 CSS 不使用 Tailwind、Bootstrap 或任何预处理器，仅依赖原生 CSS 特性（`color-mix`、`light-dark`、`!important` 重置 body 默认样式）。

### 关键文件
- `codex-rs/tui/assets/inline_visualization/visualize.css`

## 3. 非相关说明

- 仓库中没有 Tailwind、SCSS、LESS、PostCSS、组件库（如 shadcn/ui、MUI 等）或设计系统工具链。
- 没有 pnpm/npm 包中的前端样式资源（`package.json` 仅管理构建脚本，`pnpm-workspace.yaml` 仅聚合 workspace）。
- 唯一的 CSS 文件即上述 `visualize.css`，其余样式全部由 Rust ratatui 代码在运行时生成。

## 4. 规则与约束（来自权威来源）

- `codex-rs/tui/styles.md` 明确规定：
  - “Avoid unchecked custom foreground colors.”
  - “Avoid ANSI `black` & `white` as foreground colors because the default terminal theme color will do a better job.”
  - “Avoid ANSI `blue` and `yellow` because for now the style guide doesn't use them.”
  - “There are some rules to try to catch this in `clippy.toml`。”
- `visualize.css` 中注释区分 “Agent-facing contract; keep in sync with SKILL.md” 与 “Internal implementation variables; not part of the agent contract”，要求对外暴露的 token 保持稳定。
- `theme_picker.rs` 的 doc comment 描述了 `/theme` 命令的行为契约：live preview、cancel-restore、persist on confirm 到 `[tui] theme`。