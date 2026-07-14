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
        "statuses: write",
        "Publish deployment status",
        "github-pages/live",
        "Take the 90-second tour",
        "Skip to the Control Room",
        "static-bootstrap.js",
        "audit.js",
        "audit.css",
        "demo-data.json",
    }
    for fragment in required_fragments:
        assert fragment in workflow

    assert "pull_request:" not in workflow
    assert workflow.count("environment:") == 1
    assert workflow.count("actions/deploy-pages@v5") == 1
    assert "if: always()" in workflow
    assert "cancel-in-progress: false" in workflow


def test_pages_bundle_is_a_functional_project_path_safe_browser_application():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    showcase = (WEB / "showcase.js").read_text(encoding="utf-8")
    engine = (WEB / "browser-engine.js").read_text(encoding="utf-8")
    bridge = (WEB / "browser-bridge.js").read_text(encoding="utf-8")
    required = {
        "index.html",
        "styles.css",
        "refinements.css",
        "audit.css",
        "static-bootstrap.js",
        "app.js",
        "renderers.js",
        "workflow.js",
        "showcase.js",
        "audit.js",
        "browser-engine.js",
        "browser-bridge.js",
        "browser-workbench.css",
        "demo-data.json",
    }
    assert required <= {path.name for path in WEB.iterdir() if path.is_file()}
    assert {
        "cost.csv",
        "schedule.xer",
        "equations.json",
    } <= {path.name for path in (WEB / "samples").iterdir() if path.is_file()}

    local_assets = re.findall(r'(?:src|href)="\./([^"?#]+)', html)
    assert local_assets
    assert all((WEB / asset).is_file() for asset in local_assets)
    assert not re.search(r'(?:src|href)="/(?!/)', html)

    assert "Skip to the Control Room" in html
    assert 'src="./static-bootstrap.js"' in html
    assert "frame-ancestors" not in html
    assert 'id="dialogClose" type="button"' in html
    assert 'id="inspector" role="dialog"' in html
    assert 'id="evidenceGraph" role="group"' in html
    assert 'aria-selected="true"' in html
    assert 'aria-controls="panel-overview"' in html
    assert "browser-bridge.js" in showcase
    assert "analyzeForm" in engine
    assert "sha256File" in engine
    assert "restoreWorkspace" in engine
    assert "Export analysis JSON" in engine
    assert "Browser-compiled monthly close" in bridge

    payload = json.loads((WEB / "demo-data.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "eq-proof/control-room@2"
    assert payload["gate"]["status"] == "blocked"
    assert payload["portfolio"]["reported_eac"] == 407_000_000
    assert payload["portfolio"]["defensible_eac"] == 418_000_000
    assert payload["portfolio"]["exposure_above_reported_eac"] == 76_000_000


def test_browser_audit_covers_function_accessibility_and_real_workflows():
    workflow = (
        ROOT / ".github" / "workflows" / "ui-audit.yml"
    ).read_text(encoding="utf-8")
    config = (ROOT / "playwright.config.js").read_text(encoding="utf-8")
    core_spec = (ROOT / "tests" / "ui" / "control-room.spec.js").read_text(
        encoding="utf-8"
    )
    workbench_spec = (
        ROOT / "tests" / "ui" / "browser-workbench.spec.js"
    ).read_text(encoding="utf-8")

    assert "playwright install --with-deps chromium" in workflow
    assert "npm run test:browser-engine" in workflow
    assert "npm run test:ui" in workflow
    assert "Functional UI, responsive, and accessibility audit" in workflow
    assert "desktop" in config
    assert "mobile" in config
    assert "reduced-motion" in config
    assert "AxeBuilder" in core_spec
    assert "tabs expose state" in core_spec
    assert "guided review completes" in core_spec
    assert "accepts files" in workbench_spec
    assert "compiles a cost file" in workbench_spec
    assert "creates replayable evidence" in workbench_spec
    assert "Restored browser workspace" in workbench_spec
    assert "validated by the browser engine" in workbench_spec
