import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "#")


def test_relative_markdown_links_resolve():
    missing = []
    documents = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").rglob("*.md")),
    ]
    for document in documents:
        for target in LINK.findall(document.read_text(encoding="utf-8")):
            if target.startswith(EXTERNAL_PREFIXES):
                continue
            path_text = target.split("#", 1)[0]
            if not path_text:
                continue
            resolved = (document.parent / path_text).resolve()
            if not resolved.exists():
                missing.append(
                    f"{document.relative_to(ROOT)} -> {target}"
                )
    assert missing == []


def test_wiki_sidebar_local_targets_exist_and_external_targets_are_https():
    sidebar = (ROOT / "wiki/_Sidebar.md").read_text(encoding="utf-8")
    targets = LINK.findall(sidebar)
    assert targets
    for target in targets:
        if target.startswith(("http://", "https://")):
            assert target.startswith("https://")
            continue
        assert (ROOT / "wiki" / f"{target}.md").exists()
