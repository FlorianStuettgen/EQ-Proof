import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "eq_proof" / "web"
PAGES_URL = "https://florianstuettgen.github.io/EQ-Proof/"


def test_readme_exposes_the_canonical_live_application():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.count(PAGES_URL) >= 2
    assert "Take the guided Control Room tour" in readme
    assert "hosted synthetic showcase" in readme
    assert "Public synthetic showcase" in readme


def test_pages_workflow_uses_the_official_static_deployment_shape():
    workflow = (
        ROOT / ".github" / "workflows" / "pages.yml"
    ).read_text(encoding="utf-8")
    required_fragments = {
        "workflow_dispatch:",
        "branches: [main]",
        "group: pages",
        "name: Deploy GitHub Pages",
        "Validate deployable bundle",
        "Smoke-test static bundle",
        "actions/configure-pages@v5",
        "actions/upload-pages-artifact@v3",
        "actions/deploy-pages@v5",
        "url: ${{ steps.deployment.outputs.page_url }}",
        "Take the 90-second tour",
        "demo-data.json",
    }
    for fragment in required_fragments:
        assert fragment in workflow

    assert "pull_request:" not in workflow
    assert workflow.count("environment:") == 1
    assert workflow.count("actions/deploy-pages@v5") == 1
    assert "cancel-in-progress: false" in workflow


def test_pages_bundle_is_self_contained_and_project_path_safe():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    required = {
        "index.html",
        "styles.css",
        "refinements.css",
        "app.js",
        "renderers.js",
        "workflow.js",
        "showcase.js",
        "demo-data.json",
    }
    assert required <= {path.name for path in WEB.iterdir() if path.is_file()}

    local_assets = re.findall(r'(?:src|href)="\./([^"?#]+)', html)
    assert local_assets
    assert all((WEB / asset).is_file() for asset in local_assets)
    assert not re.search(r'(?:src|href)="/(?!/)', html)

    payload = json.loads((WEB / "demo-data.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "eq-proof/control-room@2"
    assert payload["gate"]["status"] == "blocked"
    assert payload["portfolio"]["reported_eac"] == 407_000_000
    assert payload["portfolio"]["defensible_eac"] == 418_000_000
    assert payload["portfolio"]["exposure_above_reported_eac"] == 76_000_000
