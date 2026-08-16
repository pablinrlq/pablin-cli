from __future__ import annotations

from pathlib import Path

from easyaws.config import (
    clear_profile_authentication,
    default_profile,
    default_region,
    discover_profiles,
)


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


def test_clears_only_authentication_for_selected_profile(tmp_path: Path) -> None:
    config = tmp_path / "config"
    credentials = tmp_path / "credentials"
    config.write_text(
        "# manter comentário\n"
        "[default]\n"
        "region = sa-east-1\n"
        "login_session = arn:aws:iam::111111111111:user/old\n"
        "role_arn = arn:aws:iam::111111111111:role/old\n"
        "[profile prod]\n"
        "region = us-east-1\n"
        "login_session = arn:aws:iam::222222222222:user/prod\n",
        encoding="utf-8",
    )
    credentials.write_text(
        "[default]\n"
        "aws_access_key_id = OLDKEY\n"
        "aws_secret_access_key = OLDSECRET\n"
        "[prod]\n"
        "aws_access_key_id = PRODKEY\n",
        encoding="utf-8",
    )

    clear_profile_authentication("default", tmp_path)

    config_text = config.read_text(encoding="utf-8")
    credentials_text = credentials.read_text(encoding="utf-8")
    assert "# manter comentário" in config_text
    assert "region = sa-east-1" in config_text
    assert "111111111111" not in config_text
    assert "222222222222" in config_text
    assert "OLDKEY" not in credentials_text
    assert "OLDSECRET" not in credentials_text
    assert "PRODKEY" in credentials_text
