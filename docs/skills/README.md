# Codex Dev Skill

这个包让支持标准 `SKILL.md` 格式的 harness 都可以使用随包提供的 Codex 中文文档。

## 包结构

```text
codex-dev/
├── SKILL.md
├── scripts/
│   └── wiki_docs.py
└── references/
    ├── wiki_docs.md
    └── repowiki/
        └── zh/
            └── content/
```

请保持 `SKILL.md`、`scripts/` 与 `references/repowiki/` 位于同一个 skill 目录中。skill 会根据自身目录定位脚本和知识资源；运行脚本需要 Python 3，不需要额外安装第三方依赖。

## 安装

将完整的 `codex-dev` 目录复制到目标 harness 选择的 skills 目录，或通过该 harness 的 skill 管理器导入。具体安装位置由使用者决定。

不要扁平化目录，也不要只复制 `SKILL.md`；`scripts/` 提供标题、行号和局部内容定位，`references/repowiki/zh/content/` 提供文档正文，都是正常工作的必要资源。包内不包含摘要卡片或生成过程元数据，避免引入重复或无关信息。

如果 harness 不会自动发现新复制的 skill，请重新加载 skill 注册表或重启会话。

## 使用

如果 harness 支持显式调用，可以使用 `/codex-dev` 激活 skill。否则，直接提出包含项目知识要求的任务，例如：

- `使用 Codex Dev，解释请求如何经过应用服务器。`
- `使用随包提供的项目知识，定位配置加载路径及其调用方。`
- `规划这个修改前，先检查相关模块的架构和编码规范。`
- `准备二次开发 Codex：先确认测试与质量门禁，再定位实现并给出验证方案。`

全部 18 个主题入口见 [SKILL.md 的“按任务路由”](codex-dev/SKILL.md#按任务路由)。路由链接相对于 `SKILL.md`，复制整个 skill 目录后仍然有效。

修改 Codex 源码时，优先查看 [SKILL.md 的“Codex 二次开发”](codex-dev/SKILL.md#codex-二次开发)。该部分链接开发环境、项目结构、测试、编码规范、调试性能和构建部署 6 个专项入口。

一般调查按“查找页面 → 查看标题 → 按行段读取”进行，文档足够时不必继续查看源码；二次开发按“开发指南 → 模块文档 → 必要的源码补充 → 焦点验证”推进。实际修改前仍须核验目标实现、直接受影响的调用方、配置约束和相关测试。

脚本只需页面名称或关键词，不需要模型查找或拼接文档路径。简明命令和示例见[脚本使用说明](codex-dev/references/wiki_docs.md)。

## 文档基线

- Codex 版本：`0.160.0`
- Commit：`36e074a2fb365aa788886495c82e6ea612226cd9`

需要更新文档时，替换 `codex-dev/references/repowiki/zh/content/`，同步更新上方及 `codex-dev/SKILL.md` 中的版本与 commit 基线，并核对路由和页面数量。包内只保留文档正文，不加入摘要卡片或生成过程元数据。
