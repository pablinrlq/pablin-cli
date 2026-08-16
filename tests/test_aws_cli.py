from __future__ import annotations

import json
import subprocess

import pytest

from easyaws.aws_cli import AwsCliError, AwsCliExecutor, AwsCommand, find_aws_binary


def test_command_keeps_each_argument_separate() -> None:
    command = AwsCommand(
        arguments=(
            "lambda",
            "update-function-configuration",
            "--function-name",
            "safe-name",
            "--memory-size",
            "512",
        ),
        description="teste",
        mutates=True,
    )

    assert command.argv[0] == "aws"
    assert command.argv[-2:] == ("--memory-size", "512")
    assert "update-function-configuration" in command.display()


def test_executor_uses_shell_false_and_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["argv"] = argv
        seen["shell"] = kwargs["shell"]
        return subprocess.CompletedProcess(argv, 0, json.dumps({"Functions": []}), "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    executor = AwsCliExecutor(binary="aws-test")
    command = AwsCommand(("lambda", "list-functions"), "listar")

    assert executor.run_json(command) == {"Functions": []}
    assert seen["argv"] == ["aws-test", "lambda", "list-functions"]
    assert seen["shell"] is False


def test_executor_can_run_non_json_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, "logout ok\n", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    executor = AwsCliExecutor(binary="aws-test")

    output = executor.run_text(AwsCommand(("logout", "--profile", "dev"), "sair"))

    assert output == "logout ok"


def test_executor_translates_missing_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 255, "", "Unable to locate credentials")

    monkeypatch.setattr(subprocess, "run", fake_run)
    executor = AwsCliExecutor(binary="aws-test")

    with pytest.raises(AwsCliError) as captured:
        executor.run_json(AwsCommand(("lambda", "list-functions"), "listar"))

    assert "credenciais" in captured.value.friendly_message


def test_finds_user_install_when_path_has_not_refreshed(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = tmp_path / "Programs" / "Amazon" / "AWSCLIV2" / "aws.exe"
    binary.parent.mkdir(parents=True)
    binary.touch()
    monkeypatch.delenv("PABLIN_AWS_BINARY", raising=False)
    monkeypatch.delenv("EASYAWS_AWS_BINARY", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "other"))
    monkeypatch.setattr("easyaws.aws_cli.shutil.which", lambda _: None)

    assert find_aws_binary() == str(binary)


def test_prefers_pablin_aws_binary_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PABLIN_AWS_BINARY", r"C:\custom\aws.exe")
    monkeypatch.setenv("EASYAWS_AWS_BINARY", r"C:\legacy\aws.exe")

    assert find_aws_binary() == r"C:\custom\aws.exe"
