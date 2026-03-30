from advanced_vision.schemas import WindowInfo
from advanced_vision.tools.windows import _select_window_candidate


def test_select_window_candidate_prefers_title_match_over_app_only_match() -> None:
    windows = [
        WindowInfo(window_id="1", title="Watch INVINCIBLE - Google Chrome", app_name="chrome", is_active=False),
        WindowInfo(window_id="2", title="Workflow Automation - n8n - Google Chrome", app_name="chrome", is_active=False),
    ]

    candidate = _select_window_candidate(windows, "workflow automation", "chrome")

    assert candidate is not None
    assert candidate.window_id == "2"


def test_select_window_candidate_can_match_app_only_when_title_not_required() -> None:
    windows = [
        WindowInfo(window_id="1", title="System Monitor", app_name="gnome-system-monitor", is_active=False),
        WindowInfo(window_id="2", title="Workflow Automation - n8n - Google Chrome", app_name="chrome", is_active=True),
    ]

    candidate = _select_window_candidate(windows, "", "chrome")

    assert candidate is not None
    assert candidate.window_id == "2"
