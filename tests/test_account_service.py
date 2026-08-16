from __future__ import annotations

import pytest

from easyaws.account_service import AccountService
from easyaws.aws_cli import AwsCliError, AwsCommand, DemoAwsCliExecutor
from easyaws.models import AwsContext


def test_reads_current_identity() -> None:
    service = AccountService(DemoAwsCliExecutor())

    identity = service.get_identity(AwsContext(profile="demo", region="sa-east-1"))

    assert identity.account_id == "123456789012"
    assert identity.principal == "demo-user"


def test_switch_clears_only_selected_profile_before_login() -> None:
    class RecordingExecutor(DemoAwsCliExecutor):
        def __init__(self) -> None:
            super().__init__()
            self.commands: list[AwsCommand] = []

        def run_text(
            self,
            command: AwsCommand,
            *,
            timeout_seconds: int | None = None,
        ) -> str:
            self.commands.append(command)
            return super().run_text(command, timeout_seconds=timeout_seconds)

    executor = RecordingExecutor()
    cleaned_profiles: list[str] = []
    service = AccountService(executor, credential_cleaner=cleaned_profiles.append)
    context = AwsContext(profile="dev", region="sa-east-1")

    identity = service.switch_account(context)

    assert identity.account_id == "999999999999"
    assert executor.commands[0].arguments[:3] == ("logout", "--profile", "dev")
    assert cleaned_profiles == ["dev"]
    assert any(
        command.arguments[:3] == ("login", "--profile", "dev")
        for command in executor.commands
    )
    assert executor.commands[-1].arguments[:2] == ("configure", "list")


def test_rejects_login_when_credential_source_is_not_login() -> None:
    service = AccountService(DemoAwsCliExecutor())

    with pytest.raises(AwsCliError, match="não está usando"):
        service._validate_login_source(
            "access_key : ******** : shared-credentials-file : ~/.aws/credentials\n"
            "secret_key : ******** : shared-credentials-file : ~/.aws/credentials"
        )
