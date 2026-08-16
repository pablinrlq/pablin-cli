from __future__ import annotations

import pytest

from easyaws.aws_cli import AwsCommand, DemoAwsCliExecutor
from easyaws.lambda_service import LambdaService
from easyaws.models import AwsContext


def test_lists_demo_functions_in_name_order() -> None:
    service = LambdaService(DemoAwsCliExecutor())

    functions = service.list_functions(AwsContext(profile="demo", region="sa-east-1"))

    assert [function.name for function in functions] == [
        "enviar-email",
        "processar-pedidos",
        "upload-imagens",
    ]


def test_memory_update_command_contains_explicit_context() -> None:
    service = LambdaService(DemoAwsCliExecutor())
    context = AwsContext(profile="prod", region="sa-east-1")

    command = service.memory_update_command(context, "processar-pedidos", 512)

    assert command.mutates is True
    assert command.arguments == (
        "lambda",
        "update-function-configuration",
        "--function-name",
        "processar-pedidos",
        "--memory-size",
        "512",
        "--region",
        "sa-east-1",
        "--profile",
        "prod",
        "--output",
        "json",
        "--no-cli-pager",
    )


@pytest.mark.parametrize("memory", [0, 127, 10_241, 99_999])
def test_rejects_invalid_memory(memory: int) -> None:
    service = LambdaService(DemoAwsCliExecutor())

    with pytest.raises(ValueError, match="memória"):
        service.memory_update_command(
            AwsContext(profile="default", region="us-east-1"),
            "function-name",
            memory,
        )


def test_rejects_values_that_could_escape_to_a_shell() -> None:
    service = LambdaService(DemoAwsCliExecutor())

    with pytest.raises(ValueError, match="Nome"):
        service.memory_update_command(
            AwsContext(profile="default", region="us-east-1"),
            "function; Remove-Item *",
            512,
        )

