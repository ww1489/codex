## 1. 采用的工具链

仓库是一个多语言 monorepo，按语言分别使用各自的包管理器，并由 Bazel MODULE.bazel 作为顶层构建图统一编排：

- **Rust**：`codex-rs/` 下的 Cargo workspace（`codex-rs/Cargo.toml`），锁文件 `codex-rs/Cargo.lock`；安全审计通过 `codex-rs/deny.toml` + `cargo-deny`。
- **TypeScript / Node.js**：根级 pnpm workspace（`pnpm-workspace.yaml`），锁文件 `pnpm-lock.yaml`，`.npmrc` 配置 hoisted 模式。
- **Python**：`scripts/pyproject.toml` + `uv.lock`（scripts 子项目）；`sdk/python/` 和 `sdk/python-runtime/` 各有一份 `pyproject.toml` + `uv.lock`。
- **Bazel**：根 `MODULE.bazel` 声明所有 Bazel module 依赖，并通过 `patches/` 目录的 patch 文件修补上游规则。
- **Nix**：根 `flake.nix` 提供开发 shell 与跨平台（x86_64/aarch64 Linux & macOS）可复现环境，版本从 `codex-rs/Cargo.toml` 读取。
- **CI 更新**：GitHub Dependabot（`.github/dependabot.yaml`）监控 bun、cargo、docker、github-actions、rust-toolchain。

## 2. 关键文件

- `MODULE.bazel`：Bazel 模块清单，集中声明 `rules_rs`、`rules_foreign_cc`、`rules_python`、`llvm`、`windows_support`、`protobuf`、`aws-lc` 等依赖，并使用 `archive_override` / `single_version_override` 进行修补与替换。
- `.bazelignore`、`.bazelrc`：Bazel 忽略规则与工作区行为。
- `codex-rs/Cargo.toml`：workspace 根，列出所有 crate members。
- `codex-rs/Cargo.lock`：Rust 依赖锁定。
- `codex-rs/deny.toml`：`cargo-deny` 策略（许可证、漏洞等）。
- `pnpm-workspace.yaml`：workspace 成员 `codex-cli`、`codex-rs/responses-api-proxy/npm`、`sdk/typescript`，并启用 `trustPolicy: no-downgrade`。
- `pnpm-lock.yaml`：Node.js 依赖锁定。
- `.npmrc`：`shamefully-hoist=true`、`strict-peer-dependencies=false`、`node-linker=hoisted`、`prefer-workspace-packages=true`。
- `scripts/pyproject.toml`、`scripts/uv.lock`：scripts 子项目的 Python 依赖。
- `sdk/python/pyproject.toml`、`sdk/python/uv.lock`：OpenAI Codex Python SDK。
- `sdk/python-runtime/pyproject.toml`、`sdk/python-runtime/uv.lock`：Python runtime。
- `flake.nix`、`flake.lock`：Nix 开发环境。
- `.github/dependabot.yaml`：Dependabot 更新策略。
- `third_party/v8/`、`third_party/openssl/`、`third_party/sqlite/`、`third_party/powershell/`、`third_party/wezterm/`、`third_party/wine/`：以 Bazel BUILD 形式 vendored 的二进制/源码依赖。
- `patches/`：针对上游 Bazel rules（如 `rules_rust`、`rules_foreign_cc`、`windows_support`、`protobuf`）的补丁集合。

## 3. 架构与约定

### 3.1 Bazel MODULE 是顶层权威
`MODULE.bazel` 是所有 Bazel 依赖的唯一声明点。第三方库通过两种方式引入：
- BCR / GitHub archive 的 `bazel_dep(name, version)`，例如 `rules_rs = "0.0.96"`、`llvm = "0.8.11"`。
- 对上游规则的修补：`single_version_override(module_name, patches=[...])` 或 `archive_override(url, integrity=...)` 将 `hermetic-llvm`、`windows_support`、`protobuf` 等替换为带补丁的版本。
Windows 工具链（MSVC 14.50.35717、Windows SDK 10.0.26100.7705）通过 `@windows_support` extension 以 sha256 integrity 下载，确保可复现。

### 3.2 Rust workspace 单源版本
`codex-rs/Cargo.toml` 中的 `[workspace.package]` 是版本唯一来源；`flake.nix` 直接 `builtins.fromTOML` 读取它来推导 Nix package 版本（release commit 用真实版本，main 分支回退到 `0.0.0-dev+<rev>`）。

### 3.3 Python 由 uv 管理
scripts 与 sdk 子项目均使用 `pyproject.toml` + `uv.lock`。`scripts/pyproject.toml` 设置 `index-strategy = "first-index"` 与 `exclude-newer = "7 days"`，限制新包的发现范围。

### 3.4 Node.js 由 pnpm 管理
workspace 仅包含三个包：`codex-cli`、`codex-rs/responses-api-proxy/npm`、`sdk/typescript`。`pnpm-workspace.yaml` 启用 `blockExoticSubdeps: true`、`strictDepBuilds: true`、`trustPolicy: no-downgrade`，并对一个来自 GitHub tarball 的非 npm registry 包 `@modelcontextprotocol/conformance` 显式 `allowBuilds`，其余 exotic subdeps 被阻断。

### 3.5 Vendored 二进制依赖
`third_party/` 下直接内联 V8、OpenSSL、SQLite、PowerShell、WezTerm、Wine 的 Bazel BUILD 定义与补丁，不经过外部包管理器。V8 还附带 `*.sha256` 校验文件（如 `rusty_v8_152_2_0.sha256`）。

## 4. 约定与约束

- **Rust 依赖锁定**：`codex-rs/Cargo.lock` 必须提交；`deny.toml` 通过 cargo-deny 在 CI 中执行许可证与漏洞检查（见 `codex-rs/.cargo/audit.toml`）。
- **pnpm trust policy**：`pnpm-workspace.yaml` 中的 `trustPolicy: no-downgrade` 禁止自动降级依赖；`minimumReleaseAge: 10080`（7 天）延迟对新包的信任。
- **pnpm exotic subdeps 阻断**：`blockExoticSubdeps: true` 阻止非 npm registry 的子依赖安装，仅允许 `@modelcontextprotocol/conformance` 通过 URL tarball 安装（显式白名单）。
- **npm peer 宽松**：`.npmrc` 设置 `strict-peer-dependencies=false`，peer 冲突不会导致安装失败。
- **Bazel 补丁优先**：所有需要修改的上游 Bazel 规则都通过 `patches/*.patch` 与 `single_version_override` / `archive_override` 引入，而不是 fork 仓库。
- **Windows 工具链完整性校验**：MSVC installer manifest 与 Windows SDK 组件均以 `sha256` 校验，禁止篡改。
- **Dependabot 周更**：`.github/dependabot.yaml` 对所有 ecosystem（bun、cargo、docker、github-actions、rust-toolchain）采用 `interval: weekly` + `cooldown.default-days: 7`，避免 PR 风暴。
- **Nix 开发环境**：`flake.nix` 固定 `nixpkgs.url = github:NixOS/nixpkgs/nixos-unstable`，并通过 `rust-overlay` 注入 rust-minimal；shellHook 强制 `CC=clang` / `CXX=clang++` 以规避 BoringSSL 编译警告。
- **Python index 策略**：`scripts/pyproject.toml` 的 `index-strategy = "first-index"` 保证首次索引命中即停止搜索，提升可复现性；`exclude-newer-span = P7D` 限制最近 7 天内发布的新包。

## 5. 未观察到的内容

- 未发现 Go 模块（无 `go.mod` / `go.sum`）。
- 未发现 Ruby Gemfile / Bundler 配置。
- 未发现 Maven / Gradle / pipenv / Poetry 等其他包管理器。
- 私有注册表未在可见配置中出现（npm 使用官方 registry，Rust 使用 crates.io）。