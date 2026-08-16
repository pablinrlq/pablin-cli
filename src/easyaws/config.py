"""Descoberta local de perfis e preferências da AWS CLI."""

from __future__ import annotations

import configparser
import os
import re
import stat
import tempfile
from pathlib import Path


AUTHENTICATION_KEYS = frozenset(
    {
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_session_token",
        "credential_process",
        "credential_source",
        "login_session",
        "role_arn",
        "source_profile",
        "sso_account_id",
        "sso_region",
        "sso_role_name",
        "sso_session",
        "sso_start_url",
        "web_identity_token_file",
    }
)
_SECTION_PATTERN = re.compile(r"^\s*\[([^]]+)]")
_OPTION_PATTERN = re.compile(r"^\s*([A-Za-z0-9_]+)\s*[:=]")


def _read_ini(path: Path) -> configparser.RawConfigParser:
    parser = configparser.RawConfigParser()
    if path.is_file():
        parser.read(path, encoding="utf-8")
    return parser


def _remove_keys_from_section(path: Path, section: str) -> bool:
    if not path.is_file():
        return False

    target = path.resolve(strict=True)
    original = target.read_text(encoding="utf-8-sig")
    updated_lines: list[str] = []
    in_target_section = False
    removed = False

    for line in original.splitlines(keepends=True):
        section_match = _SECTION_PATTERN.match(line)
        if section_match:
            in_target_section = section_match.group(1).strip() == section
            updated_lines.append(line)
            continue

        option_match = _OPTION_PATTERN.match(line) if in_target_section else None
        if option_match and option_match.group(1).lower() in AUTHENTICATION_KEYS:
            removed = True
            continue
        updated_lines.append(line)

    if not removed:
        return False

    file_mode = stat.S_IMODE(target.stat().st_mode)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            delete=False,
            dir=target.parent,
            prefix=f".{target.name}.pablin-",
        ) as temporary:
            temporary_name = temporary.name
            temporary.write("".join(updated_lines))
            temporary.flush()
            os.fsync(temporary.fileno())
        os.chmod(temporary_name, file_mode)
        os.replace(temporary_name, target)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return True


def clear_profile_authentication(
    profile: str, aws_directory: Path | None = None
) -> None:
    """Remove somente fontes de autenticação do perfil AWS selecionado."""

    if aws_directory is None:
        config_path = Path(
            os.environ.get("AWS_CONFIG_FILE", Path.home() / ".aws" / "config")
        )
        credentials_path = Path(
            os.environ.get(
                "AWS_SHARED_CREDENTIALS_FILE",
                Path.home() / ".aws" / "credentials",
            )
        )
    else:
        config_path = aws_directory / "config"
        credentials_path = aws_directory / "credentials"

    config_section = "default" if profile == "default" else f"profile {profile}"
    _remove_keys_from_section(config_path, config_section)
    _remove_keys_from_section(credentials_path, profile)


def discover_profiles(aws_directory: Path | None = None) -> list[str]:
    """Lê nomes de perfil sem acessar nem retornar segredos."""

    directory = aws_directory or Path.home() / ".aws"
    profiles: set[str] = set()

    config = _read_ini(directory / "config")
    for section in config.sections():
        if section == "default":
            profiles.add("default")
        elif section.startswith("profile "):
            profiles.add(section.removeprefix("profile ").strip())

    credentials = _read_ini(directory / "credentials")
    profiles.update(credentials.sections())

    configured = os.environ.get("AWS_PROFILE")
    if configured:
        profiles.add(configured)
    if not profiles:
        profiles.add("default")

    return sorted(profiles, key=lambda value: (value != "default", value.casefold()))


def default_profile(profiles: list[str]) -> str:
    configured = os.environ.get("AWS_PROFILE")
    if configured in profiles:
        return configured
    if "default" in profiles:
        return "default"
    return profiles[0]


def default_region(profile: str, aws_directory: Path | None = None) -> str:
    environment_region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    if environment_region:
        return environment_region

    directory = aws_directory or Path.home() / ".aws"
    config = _read_ini(directory / "config")
    section = "default" if profile == "default" else f"profile {profile}"
    if config.has_option(section, "region"):
        return config.get(section, "region").strip()
    return "us-east-1"
