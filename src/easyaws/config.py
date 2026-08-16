"""Descoberta local de perfis e preferências da AWS CLI."""

from __future__ import annotations

import configparser
import os
from pathlib import Path


def _read_ini(path: Path) -> configparser.RawConfigParser:
    parser = configparser.RawConfigParser()
    if path.is_file():
        parser.read(path, encoding="utf-8")
    return parser


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

