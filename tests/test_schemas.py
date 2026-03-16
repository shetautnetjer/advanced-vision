from advanced_vision.schemas import (
    ActionProposal,
    ActionResult,
    ScreenshotArtifact,
    VerificationResult,
    WindowInfo,
)


def test_schema_instantiation() -> None:
    screenshot = ScreenshotArtifact(path="artifacts/screens/a.png", width=100, height=200, timestamp="ts")
    window = WindowInfo(title="Editor", app_name="Code", is_active=True)
    proposal = ActionProposal(action_type="click", x=10, y=20)
    result = ActionResult(ok=True, action_type="click", message="ok")
    verification = VerificationResult(changed=True, similarity=0.8, message="changed")

    assert screenshot.width == 100
    assert window.is_active is True
    assert proposal.action_type == "click"
    assert result.ok is True
    assert verification.changed is True
