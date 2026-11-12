#!/usr/bin/env python3
"""Locate and read selected parts of bundled Codex Markdown documentation."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SKILL_ROOT = Path(__file__).resolve().parent.parent
WIKI_ROOT = SKILL_ROOT / "references" / "repowiki" / "zh" / "content"
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_PATTERN = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
MAX_OUTPUT_LINES = 500

# Windows 控制台默认可能是 GBK；脚本输出必须保留 Codex 文档 的中文路径和正文。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class Heading:
    level: int
    title: str
    line: int


def relative_path(path: Path) -> str:
    return path.relative_to(WIKI_ROOT).as_posix()


def wiki_files() -> list[Path]:
    if not WIKI_ROOT.is_dir():
        raise ValueError(f"找不到 Codex 文档 正文目录：{WIKI_ROOT}")
    return sorted(
        (path for path in WIKI_ROOT.rglob("*.md") if path.is_file()),
        key=lambda path: relative_path(path),
    )


def resolve_document(value: str) -> Path:
    query = value.strip()
    if not query:
        raise ValueError("页面名称或关键词不能为空。")
    exact = [path for path in wiki_files() if path.stem.casefold() == query.casefold()]
    if len(exact) == 1:
        return exact[0]
    matches = matching_documents(query)
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(f"找不到页面“{value}”，请先用 list 或 search 查找。")
    candidates = "、".join(relative_path(path) for path in matches[:8])
    raise ValueError(f"“{value}”匹配 {len(matches)} 个页面，请补充关键词。候选：{candidates}")


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ValueError(f"无法读取文档 {relative_path(path)}：{error}") from error


def headings(lines: Iterable[str]) -> list[Heading]:
    result: list[Heading] = []
    fence_character = ""
    fence_length = 0
    for number, line in enumerate(lines, 1):
        fence = FENCE_PATTERN.match(line)
        if fence:
            marker = fence.group(1)
            if not fence_character:
                fence_character = marker[0]
                fence_length = len(marker)
                continue
            if marker[0] == fence_character and len(marker) >= fence_length and not fence.group(2).strip():
                fence_character = ""
                fence_length = 0
            continue
        if fence_character:
            continue
        match = HEADING_PATTERN.match(line)
        if match:
            result.append(Heading(len(match.group(1)), match.group(2), number))
    return result


def matching_documents(query: str) -> list[Path]:
    terms = [term.casefold() for term in query.split() if term]
    if not terms:
        return wiki_files()
    return [
        path
        for path in wiki_files()
        if all(term in relative_path(path).casefold() for term in terms)
    ]


def print_documents(paths: Iterable[Path], limit: int) -> None:
    paths = list(paths)
    if not paths:
        print("没有匹配的 Codex 文档 页面。")
        return
    for path in paths[:limit]:
        print(relative_path(path))
    if len(paths) > limit:
        print(f"共 {len(paths)} 个匹配页面，仅显示前 {limit} 个；请增加关键词缩小范围。")


def selected_headings(items: list[Heading], query: str | None) -> list[Heading]:
    if not query:
        return items
    terms = [term.casefold() for term in query.split() if term]
    return [item for item in items if all(term in item.title.casefold() for term in terms)]


def search_content(paths: Iterable[Path], query: str, limit: int) -> None:
    terms = [term.casefold() for term in query.split() if term]
    if not terms:
        raise ValueError("搜索关键词不能为空。")
    matches: list[tuple[Path, int, str]] = []
    for path in paths:
        for number, line in enumerate(read_lines(path), 1):
            if all(term in line.casefold() for term in terms):
                matches.append((path, number, line))
    for path, number, line in matches[:limit]:
        print(f"{relative_path(path)}:{number}: {line}")
    if not matches:
        print("没有匹配的正文内容。")
    elif len(matches) > limit:
        print(f"共 {len(matches)} 条匹配，仅显示前 {limit} 条；请增加关键词或使用 --page 缩小范围。")


def print_lines(path: Path, lines: list[str], start: int, end: int) -> None:
    print(f"页面：{relative_path(path)}")
    print(f"行段：{start}-{end}")
    for number in range(start, end + 1):
        print(f"{number}: {lines[number - 1]}")


def parse_line_range(value: str, total_lines: int) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)(?:-(\d+))?", value)
    if not match:
        raise ValueError("行段格式必须是 N 或 N-M。")
    start = int(match.group(1))
    end = int(match.group(2) or start)
    if start < 1 or end < start or end > total_lines:
        raise ValueError(f"行段超出范围，文档共有 {total_lines} 行。")
    return start, end


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="定位并分段读取随 skill 提供的 Codex 文档正文。"
    )
    parser.set_defaults(command="help")
    subparsers = parser.add_subparsers(dest="command", metavar="命令")

    list_parser = subparsers.add_parser("list", help="按页面名称或关键词列出 Codex 文档 页面")
    list_parser.add_argument("query", nargs="?", default="", help="可选页面名称或关键词，多个词用空格分隔")
    list_parser.add_argument("--limit", type=int, default=50, help="最多输出的页面数量，默认 50")

    search_parser = subparsers.add_parser("search", help="按正文关键词搜索并显示行号")
    search_parser.add_argument("query", help="正文关键词，多个词必须同时出现在同一行")
    search_parser.add_argument("--page", default="", help="可选页面名称或关键词，用于缩小搜索范围")
    search_parser.add_argument("--limit", type=int, default=40, help="最多输出的匹配行数，默认 40")

    headings_parser = subparsers.add_parser("headings", help="显示页面标题及其行号")
    headings_parser.add_argument("page", help="页面名称或关键词，不需要文件路径")
    headings_parser.add_argument("--match", help="只显示包含所有关键词的标题")

    read_parser = subparsers.add_parser("read", help="按行段读取页面内容")
    read_parser.add_argument("page", help="页面名称或关键词，不需要文件路径")
    read_parser.add_argument("--lines", required=True, metavar="N-M", help="读取 1-based 行段，例如 40-85")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "help":
            parser.print_help()
            return 0
        if args.command == "list":
            if args.limit < 1 or args.limit > 200:
                raise ValueError("文档列表的 --limit 必须在 1-200 之间。")
            print_documents(matching_documents(args.query), args.limit)
            return 0
        if args.command == "search":
            if args.limit < 1 or args.limit > 200:
                raise ValueError("正文搜索的 --limit 必须在 1-200 之间。")
            search_content(matching_documents(args.page), args.query, args.limit)
            return 0
        path = resolve_document(args.page)
        lines = read_lines(path)
        if args.command == "headings":
            print(f"页面：{relative_path(path)}")
            matches = selected_headings(headings(lines), args.match)
            if not matches:
                print("没有匹配的标题。")
            for item in matches:
                print(f"{item.line}: {'#' * item.level} {item.title}")
            return 0
        first, last = parse_line_range(args.lines, len(lines))
        if last - first + 1 > MAX_OUTPUT_LINES:
            raise ValueError(f"单次读取最多 {MAX_OUTPUT_LINES} 行，请缩小行段。")
        print_lines(path, lines, first, last)
        return 0
    except ValueError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
