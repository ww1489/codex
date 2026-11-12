# Codex 文档定位脚本

[scripts/wiki_docs.py](../scripts/wiki_docs.py) 用四个命令查找并局部读取 Codex 文档，只依赖 Python 3 标准库。脚本和文档的位置都已固定在 Skill 包内，不要搜索其他副本或拼接文档路径。

示例中的 `<skill>` 指本 Skill 所在目录。页面参数只写名称或关键词，例如 `架构总览`、`开发指南`、`项目结构`，不需要目录或 `.md` 后缀。

## 四个命令

| 命令 | 用途 |
| --- | --- |
| `list [关键词] [--limit N]` | 按名称查找页面 |
| `search 正文关键词 [--page 页面关键词] [--limit N]` | 搜索正文，返回页面和行号 |
| `headings 页面 [--match 关键词]` | 查看标题和行号 |
| `read 页面 --lines N-M` | 读取指定行段 |

## 使用步骤

不知道页面在哪里时，先查找；已经知道页面名时，直接看标题。

```bash
python "<skill>/scripts/wiki_docs.py" list "线程"
python "<skill>/scripts/wiki_docs.py" search "配置层" --page "安装与配置" --limit 10
```

查看标题，选择要读的行号。

```bash
python "<skill>/scripts/wiki_docs.py" headings "架构总览" --match "依赖"
```

按行段读取，例如读取上面查到的 443 行起的内容。

```bash
python "<skill>/scripts/wiki_docs.py" read "架构总览" --lines "443-496"
```

## 注意事项

- 页面名精确匹配入口或页面；关键词匹配到多个页面时，脚本会列出候选，补充关键词即可。
- `read --lines` 也接受单行号 `N`，单次最多读取 500 行；长内容分段继续读。
- `list` 和 `search` 的 `--limit` 范围为 1–200，默认分别输出 50 个页面和 40 条匹配。
- 搜索没有结果时更换关键词；文档没搜到不代表功能不存在。
