## 概览

Codex 仓库是一个跨语言（Rust 为主、辅以 Python/TypeScript/Node）的多 crate monorepo，采用**分层构建系统**：

- **Bazel**（`MODULE.bazel`、`bazel/`、各子 crate `BUILD.bazel`）作为主构建系统与依赖解析器，负责 Rust crate 的编译、测试、代码生成与产物打包。
- **Cargo**（`codex-rs/Cargo.toml`、`rust-toolchain.toml`）保留为本地开发入口和独立发布通道。
- **Nix flake**（`flake.nix`）提供可复现的开发环境（devShell），读取 `codex-rs/Cargo.toml` 中的工作区版本。
- **pnpm**（`pnpm-workspace.yaml`、`package.json`）管理 Node/TypeScript SDK。
- **justfile** 作为用户级任务编排层，把 Bazel、Cargo、Python 脚本统一暴露为 `just` 命令。
- **GitHub Actions**（`.github/workflows/*.yml`）驱动 CI 与 release，按 tag `rust-v*.*.*` 触发。

## 关键文件

- `MODULE.bazel`、`bazel/`：Bazel workspace 根与自定义 Starlark rules（`rules/runtime_package.bzl`、`extensions/codex_release_archive.bzl`、`platforms/release_binaries.bzl`、`toolchains/prost/` 等）。
- `.bazelrc`、`rbe.bzl`、`patches/`：Bazel 编译选项、RBE 远程执行配置与第三方补丁集合。
- `justfile`：开发者任务入口（`just test`、`just build-for-release`、`just bazel-test`、`just fmt` 等）。
- `scripts/build_codex_package.py` → `scripts/codex_package/`：构建最终分发包目录与归档（tar.gz/tgz/tar.zst/zip），支持多 target 变体。
- `scripts/stage_npm_packages.py`、`scripts/bundle_winget_package.py`：npm / Windows Store 包装。
- `.github/workflows/rust-release.yml`：release 流水线（tag 校验、macOS codesign、Linux musl、DMG 构建）。
- `flake.nix`：Nix devShell，固定 rust-overlay、clang、openssl。
- `codex-rs/rust-toolchain.toml`、`codex-rs/clippy.toml`、`codex-rs/deny.toml`：Rust toolchain 与 lint 策略。
- `docs/bazel.md`：Bazel 使用文档。

## 架构与约定

1. **Bazel 优先，Cargo 辅助**：所有 crate 都有 `BUILD.bazel`；`just test` 默认走 `cargo nextest run --no-fail-fast`，但 `just bazel-test` 走 `bazel test //...`。E2E benchmark 明确通过 Bazel 运行（`bazel test //codex-rs:e2e-benchmarks`），以保证优化构建一致性。
2. **版本单一事实源**：workspace 版本位于 `codex-rs/Cargo.toml` 的 `[workspace.package]`；Nix flake 直接 `builtins.fromTOML` 读取；release workflow 用 `grep -m1 '^version' codex-rs/Cargo.toml` 校验 tag 与之相等。
3. **Release 触发机制**：仅响应 `push: tags: ["rust-v*.*.*"]`，且 tag 必须匹配 `rust-vMAJOR.MINOR.PATCH[-prerelease][+build]`（由 `.github/scripts/releases.py` 校验）。Tag 版本号必须与 `Cargo.toml` 一致，否则失败。
4. **目标平台矩阵**：release 构建覆盖 `aarch64-apple-darwin`、`x86_64-apple-darwin`、`x86_64-unknown-linux-musl`、`aarch64-unknown-linux-musl`；Linux 产出 MUSL 链接的可执行文件；macOS 同时构建 DMG（仅 primary bundle）并进入受保护的 `codesigning` Azure Key Vault 环境签名。
5. **产物变体**：`primary`（含 `codex`、`codex-code-mode-host`、`codex-exec-server`、`codex-responses-api-proxy`、`bwrap`）与 `app-server`（`codex-app-server`、`codex-code-mode-host`、`codex-exec-server`）两套 bundle。
6. **Bazel 锁文件管控**：`just bazel-lock-check` 调用 `scripts/check-module-bazel-lock.sh`，在 Unix 上要求 lockfile 精确匹配，Windows 上回退到 `bazel mod deps --lockfile_mode=error`。
7. **构建产物命名**：通过 `ARTIFACT_SUFFIX` 环境变量区分 `cargo` 与 `bazel` 构建（当前注释注明 "Bazel releases are disabled while the BuildBuddy key is revoked"，matrix 中 `build-system: [cargo]`）。
8. **符号剥离**：`scripts/codex_package/symbols.py` 提供 strip 能力，CLI 支持 `--strip auto|all|none`，默认对 source-built release-profile 输入自动剥离。
9. **开发环境**：`just install` 在 Unix 上等价于 `rustup show active-toolchain && cargo fetch`，Windows 先安装 PowerShell 再执行同样流程；Nix 用户可直接 `nix develop`，devShell 固定 CC=CXX=clang 以规避 GCC 15 warnings-as-errors。
10. **CI 分片**：`rust-ci.yml`、`rust-ci-full.yml`、`rust-ci-full-nextest-platform.yml`、`python-sdk-build.yml`、`python-runtime-build.yml`、`sdk.yml`、`repo-checks.yml`、`blob-size-policy.yml`、`cargo-deny.yml` 等分别承担不同职责；`postmerge-ci.yml` 处理 merge 后的增量任务。

## 约定与约束

- **Release 必须打 tag**：`.github/workflows/rust-release.yml` 显式拒绝非 tag 推送（`[[ "${GITHUB_REF_TYPE}" == "tag" ]] || { echo "❌ Not a tag ref"; exit 1; }`）。
- **Tag 格式强制**：tag 必须匹配 `rust-v*.*.*`，并通过 `.github/scripts/releases.py` 进行语义化版本校验。
- **版本一致性强制**：tag 版本号必须等于 `codex-rs/Cargo.toml` 中 `version` 字段，不等则 workflow 失败。
- **Bazel MODULE.bazel.lock 必须锁定**：`just bazel-lock-check` 在 Unix 上调用专用脚本校验，Windows 上以 `--lockfile_mode=error` 报错；更新需运行 `just bazel-lock-update` 并提交新锁文件。
- **最小栈大小**：`justfile` 定义 `rust_min_stack := "8388608"`（8 MiB），test 任务设置 `RUST_MIN_STACK={{ rust_min_stack }}`，确保测试与 CI 行为一致。
- **nextest 禁止 fail-fast**：`just test` 始终带 `--no-fail-fast`，以便收集全部测试结果。
- **Workspace crate features 被禁止**：`just test` 注释说明 "Workspace crate features are banned, so there should be no need to add `--all-features`"，由 clippy/Bazel 规则实际强制执行（见 `clippy.toml`、`bazel/rules/`）。
- **Linux 发布二进制必须是 MUSL 链接**：workflow matrix 中 Linux 目标均为 `-unknown-linux-musl`，注释称 "Release artifacts intentionally ship MUSL-linked Linux binaries"。
- **macOS 二进制需在受保护环境签名**：release workflow 注释指出 "sign macOS binaries and DMGs through the protected `codesigning` GitHub environment and Azure Key Vault"。
- **Blob 大小受策略限制**：`.github/workflows/blob-size-policy.yml` + `scripts/check_blob_size.py` + `github/blob-size-allowlist.txt` 构成提交 blob 大小检查管线。
- **Python 依赖锁定**：`scripts/uv.lock` 与 `sdk/python/uv.lock` 各自锁定 Python 依赖；`scripts/pyproject.toml` 声明构建脚本依赖。
- **pnpm 工作区**：根 `pnpm-workspace.yaml` 与 `package.json` 管理 TypeScript SDK 与通用脚本。

## 典型命令

| 用途 | 命令 |
|---|---|
| 本地构建 | `just codex <args>` 或 `bazel run //codex-rs/cli:codex` |
| 运行测试 | `just test`（nextest）/ `just bazel-test` |
| 格式化 | `just fmt` / `just fmt-check` |
| Clippy | `just clippy` / `just bazel-clippy` |
| E2E benchmark | `just bench-e2e` |
| 构建发布包 | `just build-for-release`（Bazel）或 `just assemble-codex-package`（Cargo 产物组装） |
| 更新 Bazel 锁 | `just bazel-lock-update` |
| Nix 开发环境 | `nix develop` |