"""Construção segura de comandos para qualquer serviço da AWS CLI."""

from __future__ import annotations

import json
import os
import re
import shlex
from enum import Enum

from .aws_cli import AwsCommand, CommandExecutor
from .lambda_service import validate_context
from .models import AwsContext

_TOKEN_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_READ_ONLY_PREFIXES = (
    "batch-get-",
    "check-",
    "describe-",
    "detect-",
    "download-",
    "get-",
    "head-",
    "list-",
    "lookup-",
    "query",
    "scan",
    "search-",
    "select-",
    "validate-",
)
_DESTRUCTIVE_PREFIXES = (
    "cancel-",
    "delete-",
    "deregister-",
    "detach-",
    "disable-",
    "disassociate-",
    "purge-",
    "release-",
    "remove-",
    "revoke-",
    "stop-",
    "terminate-",
)
_BLOCKED_EXTRA_OPTIONS = {
    "--ca-bundle",
    "--endpoint-url",
    "--generate-cli-skeleton",
    "--no-sign-request",
    "--no-verify-ssl",
    "--output",
    "--profile",
    "--region",
}


class RiskLevel(str, Enum):
    READ_ONLY = "somente leitura"
    MUTATING = "altera recursos"
    DESTRUCTIVE = "pode remover/interromper recursos"


def classify_operation(operation: str) -> RiskLevel:
    if operation.startswith(_READ_ONLY_PREFIXES):
        return RiskLevel.READ_ONLY
    if operation.startswith(_DESTRUCTIVE_PREFIXES):
        return RiskLevel.DESTRUCTIVE
    return RiskLevel.MUTATING


class UniversalAwsService:
    def __init__(self, executor: CommandExecutor) -> None:
        self.executor = executor

    @staticmethod
    def validate_token(value: str, label: str) -> None:
        if not _TOKEN_PATTERN.fullmatch(value):
            raise ValueError(f"{label} AWS inválido: {value}")

    def skeleton_command(self, service: str, operation: str) -> AwsCommand:
        self.validate_token(service, "Serviço")
        self.validate_token(operation, "Operação")
        return AwsCommand(
            arguments=(
                service,
                operation,
                "--generate-cli-skeleton",
                "input",
                "--no-cli-pager",
            ),
            description=f"Gerar formulário local para {service} {operation}",
        )

    def input_skeleton(self, service: str, operation: str) -> str:
        command = self.skeleton_command(service, operation)
        output = self.executor.run_text(command)
        if not output:
            return "{}"
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            return "{}"
        return json.dumps(parsed, indent=2, ensure_ascii=False)

    def build_command(
        self,
        context: AwsContext,
        service: str,
        operation: str,
        payload: str,
        extra_arguments: str = "",
    ) -> AwsCommand:
        validate_context(context)
        self.validate_token(service, "Serviço")
        self.validate_token(operation, "Operação")

        arguments: list[str] = [service, operation]
        cleaned_payload = payload.strip()
        if cleaned_payload and cleaned_payload != "{}":
            try:
                parsed = json.loads(cleaned_payload)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"JSON inválido na linha {error.lineno}, coluna {error.colno}: {error.msg}"
                ) from error
            if not isinstance(parsed, dict):
                raise ValueError("O formulário JSON precisa conter um objeto na raiz.")
            arguments.extend(
                ("--cli-input-json", json.dumps(parsed, separators=(",", ":")))
            )

        extras = shlex.split(extra_arguments, posix=os.name != "nt")
        for value in extras:
            option = value.split("=", 1)[0]
            if option in _BLOCKED_EXTRA_OPTIONS:
                raise ValueError(f"A opção {option} é controlada pelo Pablin CLI.")
        arguments.extend(extras)
        arguments.extend(context.global_arguments())

        risk = classify_operation(operation)
        return AwsCommand(
            arguments=tuple(arguments),
            description=f"Executar {service} {operation}",
            mutates=risk is not RiskLevel.READ_ONLY,
        )

    def execute(self, command: AwsCommand) -> str:
        return self.executor.run_text(command, timeout_seconds=600)
