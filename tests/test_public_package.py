from __future__ import annotations

from easyaws import __version__ as core_version
from pablin_cli import __version__ as public_version


def test_public_package_exposes_core_version() -> None:
    assert public_version == core_version
