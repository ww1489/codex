---
name: codex-dev
description: 使用随 skill 提供的 Codex 中文文档，支持架构调查、二次开发、故障排查和变更规划。通过脚本按需读取开发指南和模块文档；文档不足或需要实施修改时再查看当前源码。
---

# Codex Dev

随包提供 158 篇 Codex 中文文档，用脚本按页名或关键词定位并局部读取，用于架构调查、二次开发、配置与故障排查。文档回答不了的问题再查源码，避免无关文件调查。

## 按任务路由

下表覆盖全部 **18 个顶层入口、158 篇正文**，目录规模包含入口页。链接相对于本 `SKILL.md`；Agent 应使用脚本局部读取，不要因打开链接而加载全文。

| 任务主题 | 文档入口 | 规模 |
| --- | --- | ---: |
| 项目定位、结构、核心组件和术语 | [项目概览](references/repowiki/zh/content/项目概览.md) | 1 篇 |
| 首次安装、初始化和基本使用 | [快速开始](references/repowiki/zh/content/快速开始.md) | 1 篇 |
| 整体架构、进程协作和依赖 | [架构总览](references/repowiki/zh/content/架构总览/架构总览.md) | 34 篇 |
| 会话、回合、上下文、工具和记忆 | [智能体核心](references/repowiki/zh/content/智能体核心/智能体核心.md) | 33 篇 |
| TUI、渲染、快捷键和终端交互 | [交互式终端界面](references/repowiki/zh/content/交互式终端界面/交互式终端界面.md) | 17 篇 |
| 命令、参数、退出行为和 Shell 集成 | [命令行参考](references/repowiki/zh/content/命令行参考/命令行参考.md) | 11 篇 |
| 自动化、批处理和 CI/CD 执行 | [非交互执行](references/repowiki/zh/content/非交互执行.md) | 1 篇 |
| Python 或 TypeScript 程序化集成 | [SDK 参考](<references/repowiki/zh/content/SDK 参考/SDK 参考.md>) | 3 篇 |
| 安装、配置加载、Profile 和环境变量 | [安装与配置](references/repowiki/zh/content/安装与配置/安装与配置.md) | 17 篇 |
| 命令执行、沙箱和执行策略 | [执行环境](references/repowiki/zh/content/执行环境/执行环境.md) | 5 篇 |
| App Server、WebSocket、HTTP 和 MCP 协议 | [网络与协议](references/repowiki/zh/content/网络与协议/网络与协议.md) | 6 篇 |
| SQLite、线程历史、迁移和持久化 | [数据存储](references/repowiki/zh/content/数据存储/数据存储.md) | 9 篇 |
| 插件、Skill、Hook 和连接器 | [扩展系统](references/repowiki/zh/content/扩展系统/扩展系统.md) | 5 篇 |
| 登录、凭据、令牌和认证安全 | [认证与安全](references/repowiki/zh/content/认证与安全/认证与安全.md) | 5 篇 |
| Guardian 审查与回归；CLI `review` 见命令行参考 | [代码审查](references/repowiki/zh/content/代码审查.md) | 1 篇 |
| 开发环境、测试、构建和代码规范 | [开发指南](references/repowiki/zh/content/开发指南/开发指南.md) | 7 篇 |
| 安装、配置、网络和沙箱故障 | [故障排除](references/repowiki/zh/content/故障排除.md) | 1 篇 |
| 配置项、API、术语和兼容性速查 | [附录](references/repowiki/zh/content/附录.md) | 1 篇 |

先选择一个最相关入口，确需跨子系统时再补充；入口不明确时才使用 `list` 或 `search`。

## Codex 二次开发

修改源码时，先读[开发指南](references/repowiki/zh/content/开发指南/开发指南.md)中的相关章节，再按任务路由选择模块文档，不要顺序读完整个开发指南。

- 准备与结构：[开发环境搭建](references/repowiki/zh/content/开发指南/开发环境搭建.md)、[项目结构](references/repowiki/zh/content/开发指南/项目结构.md)。
- 实施与质量：[测试指南](references/repowiki/zh/content/开发指南/测试指南.md)、[编码规范](references/repowiki/zh/content/开发指南/编码规范.md)。
- 排查与交付：[调试与性能分析](references/repowiki/zh/content/开发指南/调试与性能分析.md)、[构建与部署](references/repowiki/zh/content/开发指南/构建与部署.md)。

按“明确行为 → 必要文档 → 当前实现与测试 → 焦点验证”推进。文档中的版本号和命令可能随代码变化，执行前核对当前 `justfile`、工具链配置、构建脚本和 CI。

## 使用规则

1. 用脚本按页面名称或关键词定位，再用 `headings` 看标题、`read` 按行段读取；不要搜索或拼接文档路径。命令见[脚本使用说明](references/wiki_docs.md)。
2. 文档足够时停止扩展阅读。信息缺失、基线较旧、引用失配、内容冲突，或需要精确接口、调用关系和失败路径时，再从文档的源码引用开始按需查看当前源码。
3. 实际修改前，即使文档完整，也要核验目标实现、直接受影响的调用方、配置约束和相关测试；修改后运行焦点测试及必要的行为检查，并说明未执行的验证。
4. Git 可用时，将当前提交与文档基线 commit 比较。基线不同或内容与当前实现冲突时，以当前源码、配置、测试和运行行为为准；文档无结果不代表功能不存在。
5. 区分随包文档信息与已验证的当前实现。未查看源码时，不要声称已验证实现。

## 资源

文档位于 `references/repowiki/zh/content/`，根据本 `SKILL.md` 所在目录解析，不要相对于当前工作目录解析。文档基线为 Codex `0.160.0`，commit `36e074a2fb365aa788886495c82e6ea612226cd9`；不要将这些资源用于其他仓库。
