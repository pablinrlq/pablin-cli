from __future__ import annotations

from pathlib import Path

from easyaws.config import default_profile, default_region, discover_profiles


def test_discovers_profiles_and_region(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "config").write_text(
        "[default]\nregion = sa-east-1\n[profile prod]\nregion = us-east-1\n",
        encoding="utf-8",
    )
    (tmp_path / "credentials").write_text("[dev]\n", encoding="utf-8")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    profiles = discover_profiles(tmp_path)

    assert profiles == ["default", "dev", "prod"]
    assert default_profile(profiles) == "default"
    assert default_region("prod", tmp_path) == "us-east-1"

