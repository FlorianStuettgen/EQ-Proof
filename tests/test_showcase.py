from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "eq_proof" / "web"


def test_showcase_surface_exposes_guided_decision_workflow():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    required_ids = {
        "guidedDemoButton",
        "workspaceTourButton",
        "downloadBriefButton",
        "tourCard",
        "tourProgress",
        "showcaseReported",
        "showcaseDefensible",
        "showcaseGap",
        "showcaseRiskAdjusted",
        "showcaseExposure",
    }
    for identifier in required_ids:
        assert f'id="{identifier}"' in html
    assert "Take the 90-second tour" in html
    assert "Not another dashboard. A reproducible decision system." in html
    assert "full test matrix enforced" in html
    assert "automated tests" not in html
    assert "no telemetry" in html.lower()


def test_showcase_javascript_preserves_semantic_boundaries():
    script = (WEB / "showcase.js").read_text(encoding="utf-8")
    engine = (WEB / "browser-engine.js").read_text(encoding="utf-8")
    assert script.count("eyebrow: 'Step ") == 5
    assert "deterministic contradiction—not a risk opinion" in script
    assert "source record → failed equation" in script
    assert "schedule_assurance" in engine
    assert "severity heuristic, not a probability" in script
    assert "does not certify contractual truth" in script
    assert "buildExecutiveBrief" in script
    assert "source_manifest" in script


def test_workflow_loads_showcase_only_after_core_initialization():
    workflow = (WEB / "workflow.js").read_text(encoding="utf-8")
    assert "init().then(() =>" in workflow
    assert "showcase.src = './showcase.js'" in workflow


def test_readme_and_case_study_present_the_same_showcase():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    case_study = (ROOT / "docs" / "SHOWCASE.md").read_text(encoding="utf-8")
    assert "Take the guided Control Room tour" in readme
    assert "docs/SHOWCASE.md" in readme
    assert "$11M" in readme and "$65M" in readme and "$76M" in readme
    assert "The 90-second demonstration" in case_study
    assert "compiler for the acceptance logic" in case_study
    assert "exact test count" in readme.lower()
    assert "exact test count" in case_study.lower()
