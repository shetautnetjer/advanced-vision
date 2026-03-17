from pathlib import Path

from PIL import Image

from advanced_vision.tools.video import _get_kimi_config, _load_env_file, extract_keyframes


def test_load_env_file_sets_missing_values(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("KIMI_API_KEY=test-key\nKIMI_MODEL=kimi-k2-5\n", encoding="utf-8")
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    monkeypatch.delenv("KIMI_MODEL", raising=False)

    _load_env_file(env_file)

    api_key, _, model = _get_kimi_config()
    assert api_key == "test-key"
    assert model == "kimi-k2-5"


def test_extract_keyframes_raises_for_missing_video(tmp_path: Path) -> None:
    missing = tmp_path / "missing.mp4"
    try:
        extract_keyframes(missing)
    except FileNotFoundError:
        assert True
    else:
        raise AssertionError("Expected FileNotFoundError")
