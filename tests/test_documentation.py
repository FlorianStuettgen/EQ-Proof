import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def test_relative_markdown_links_resolve():
    missing = []
    for document in [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]:
        for target in LINK.findall(document.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_text = target.split("#", 1)[0]
            if not path_text:
                continue
            resolved = (document.parent / path_text).resolve()
            if not resolved.exists():
                missing.append(f"{document.relative_to(ROOT)} -> {target}")
    assert missing == []


def test_wiki_sidebar_targets_exist():
    sidebar = (ROOT / "wiki/_Sidebar.md").read_text(encoding="utf-8")
    targets = LINK.findall(sidebar)
    assert targets
    for target in targets:
        assert (ROOT / "wiki" / f"{target}.md").exists()
