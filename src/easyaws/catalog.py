"""Descoberta dinâmica do catálogo instalado da AWS CLI."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .aws_cli import AwsCliError, find_aws_binary

_BUILTIN_COMMANDS = {
    "agent-toolkit",
    "cli-dev",
    "configure",
    "deploy",
    "history",
    "login",
    "logout",
    "update",
}


def find_aws_completer() -> str | None:
    configured = os.environ.get("PABLIN_AWS_COMPLETER") or os.environ.get(
        "EASYAWS_AWS_COMPLETER"
    )
    if configured:
        return configured

    from_path = shutil.which("aws_completer")
    if from_path:
        return from_path

    aws_binary = find_aws_binary()
    if aws_binary:
        sibling = Path(aws_binary).with_name("aws_completer.exe")
        if sibling.is_file():
            return str(sibling)

    candidates = [
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Programs"
        / "Amazon"
        / "AWSCLIV2"
        / "aws_completer.exe",
        Path(os.environ.get("ProgramFiles", ""))
        / "Amazon"
        / "AWSCLIV2"
        / "aws_completer.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


class AwsCliCatalog:
    """Usa o completador oficial para refletir exatamente a versão instalada."""

    def __init__(self, completer: str | None = None) -> None:
        self.completer = completer or find_aws_completer()
        self._services: list[str] | None = None
        self._operations: dict[str, list[str]] = {}
        self._parameters: dict[tuple[str, str], list[str]] = {}

    def _complete(self, line: str) -> list[str]:
        if not self.completer:
            raise AwsCliError("O completador da AWS CLI não foi encontrado.")
        environment = os.environ.copy()
        environment["COMP_LINE"] = line
        environment["COMP_POINT"] = str(len(line))
        try:
            completed = subprocess.run(
                [self.completer],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
                shell=False,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise AwsCliError(f"Não foi possível consultar o catálogo AWS: {error}") from error
        if completed.returncode != 0:
            raise AwsCliError(
                completed.stderr.strip() or "O catálogo da AWS CLI retornou um erro."
            )
        return sorted(
            {value.strip() for value in completed.stdout.splitlines() if value.strip()},
            key=str.casefold,
        )

    def list_services(self) -> list[str]:
        if self._services is None:
            self._services = [
                value
                for value in self._complete("aws ")
                if not value.startswith("-") and value not in _BUILTIN_COMMANDS
            ]
        return list(self._services)

    def list_operations(self, service: str) -> list[str]:
        if service not in self.list_services():
            raise ValueError(f"Serviço AWS desconhecido: {service}")
        if service not in self._operations:
            self._operations[service] = [
                value
                for value in self._complete(f"aws {service} ")
                if not value.startswith("-")
            ]
        return list(self._operations[service])

    def list_parameters(self, service: str, operation: str) -> list[str]:
        if operation not in self.list_operations(service):
            raise ValueError(f"Operação desconhecida para {service}: {operation}")
        key = (service, operation)
        if key not in self._parameters:
            self._parameters[key] = [
                value
                for value in self._complete(f"aws {service} {operation} --")
                if value.startswith("--")
            ]
        return list(self._parameters[key])


class DemoAwsCliCatalog(AwsCliCatalog):
    """Catálogo pequeno, porém representativo, para o modo de demonstração."""

    SERVICES = {
        "cloudformation": ["create-stack", "delete-stack", "describe-stacks", "list-stacks"],
        "dynamodb": ["create-table", "delete-table", "describe-table", "list-tables", "scan"],
        "ec2": ["describe-instances", "run-instances", "start-instances", "stop-instances", "terminate-instances"],
        "lambda": ["create-function", "delete-function", "get-function", "invoke", "list-functions", "update-function-configuration"],
        "s3api": ["create-bucket", "delete-bucket", "get-object", "list-buckets", "list-objects-v2", "put-object"],
        "sqs": ["create-queue", "delete-queue", "get-queue-attributes", "list-queues", "send-message"],
    }

    def __init__(self) -> None:
        super().__init__(completer="demo")

    def list_services(self) -> list[str]:
        return sorted(self.SERVICES)

    def list_operations(self, service: str) -> list[str]:
        if service not in self.SERVICES:
            raise ValueError(f"Serviço AWS desconhecido: {service}")
        return sorted(self.SERVICES[service])

    def list_parameters(self, service: str, operation: str) -> list[str]:
        if operation not in self.list_operations(service):
            raise ValueError(f"Operação desconhecida para {service}: {operation}")
        return ["--cli-input-json", "--profile", "--region"]
