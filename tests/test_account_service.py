from __future__ import annotations

from easyaws.account_service import AccountService
from easyaws.aws_cli import AwsCommand, DemoAwsCliExecutor
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
    service = AccountService(executor)
    context = AwsContext(profile="dev", region="sa-east-1")

    identity = service.switch_account(context)

    assert identity.account_id == "999999999999"
    assert executor.commands[0].arguments[:3] == ("logout", "--profile", "dev")
    unset_commands = [
        command
        for command in executor.commands
        if command.arguments[:2] == ("configure", "unset")
    ]
    assert len(unset_commands) == 5
    assert all(command.arguments[-2:] == ("--profile", "dev") for command in unset_commands)
    assert executor.commands[-1].arguments[:3] == ("login", "--profile", "dev")
