"""Operações de Lambda disponíveis no MVP."""

from __future__ import annotations

import re

from .aws_cli import AwsCommand, CommandExecutor
from .models import AwsContext, LambdaFunction

_PROFILE_PATTERN = re.compile(r"^[A-Za-z0-9_+=,.@-]{1,128}$")
_REGION_PATTERN = re.compile(r"^[a-z]{2}(?:-[a-z0-9]+)+-\d+$")
_FUNCTION_PATTERN = re.compile(r"^[A-Za-z0-9-_]{1,64}$")


def validate_context(context: AwsContext) -> None:
    if not _REGION_PATTERN.fullmatch(context.region):
        raise ValueError("Região inválida. Exemplo esperado: us-east-1 ou sa-east-1.")
    if context.profile and not _PROFILE_PATTERN.fullmatch(context.profile):
        raise ValueError("O nome do perfil contém caracteres inválidos.")


def validate_function_name(name: str) -> None:
    if not _FUNCTION_PATTERN.fullmatch(name):
        raise ValueError("Nome de função Lambda inválido.")


def validate_memory_size(memory_size: int) -> None:
    if not 128 <= memory_size <= 10_240:
        raise ValueError("A memória deve estar entre 128 e 10240 MB.")


class LambdaService:
    def __init__(self, executor: CommandExecutor) -> None:
        self.executor = executor

    def list_command(self, context: AwsContext) -> AwsCommand:
        validate_context(context)
        return AwsCommand(
            arguments=("lambda", "list-functions", *context.global_arguments()),
            description="Listar funções Lambda",
        )

    def list_functions(self, context: AwsContext) -> list[LambdaFunction]:
        response = self.executor.run_json(self.list_command(context))
        values = response.get("Functions", [])
        if not isinstance(values, list):
            raise ValueError("A AWS retornou uma lista de funções em formato inesperado.")
        functions = [
            LambdaFunction.from_aws(item)
            for item in values
            if isinstance(item, dict) and item.get("FunctionName")
        ]
        return sorted(functions, key=lambda function: function.name.casefold())

    def memory_update_command(
        self,
        context: AwsContext,
        function_name: str,
        memory_size: int,
    ) -> AwsCommand:
        validate_context(context)
        validate_function_name(function_name)
        validate_memory_size(memory_size)
        return AwsCommand(
            arguments=(
                "lambda",
                "update-function-configuration",
                "--function-name",
                function_name,
                "--memory-size",
                str(memory_size),
                *context.global_arguments(),
            ),
            description=f"Alterar memória de {function_name} para {memory_size} MB",
            mutates=True,
        )

    def update_memory(
        self,
        context: AwsContext,
        function_name: str,
        memory_size: int,
    ) -> dict[str, object]:
        command = self.memory_update_command(context, function_name, memory_size)
        return self.executor.run_json(command)

