"""Construção e execução segura de comandos da AWS CLI."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class AwsCommand:
    """Um comando AWS já tokenizado, nunca uma string para o shell."""

    arguments: tuple[str, ...]
    description: str
    mutates: bool = False

    @property
    def argv(self) -> tuple[str, ...]:
        return ("aws", *self.arguments)

    def display(self) -> str:
        """Formata apenas para visualização; não é usado na execução."""

        if os.name == "nt":
            return subprocess.list2cmdline(list(self.argv))
        return shlex.join(self.argv)


class CommandExecutor(Protocol):
    def run_json(self, command: AwsCommand) -> dict[str, Any]: ...

    def run_text(
        self, command: AwsCommand, *, timeout_seconds: int | None = None
    ) -> str: ...


class AwsCliError(RuntimeError):
    """Erro da AWS CLI traduzível para uma mensagem útil na interface."""

    def __init__(
        self,
        message: str,
        *,
        command: AwsCommand | None = None,
        return_code: int | None = None,
        stderr: str = "",
    ) -> None:
        super().__init__(message)
        self.command = command
        self.return_code = return_code
        self.stderr = stderr

    @property
    def friendly_message(self) -> str:
        source = f"{self} {self.stderr}".lower()
        if "unable to locate credentials" in source:
            return "Não encontrei credenciais. Configure um perfil com `aws configure`."
        if "expiredtoken" in source or "token has expired" in source:
            return "A sessão AWS expirou. Renove o login do perfil e tente novamente."
        if "accessdenied" in source or "not authorized" in source:
            return "O perfil atual não tem permissão para executar esta operação."
        if "could not connect" in source or "endpointurl" in source:
            return "Não foi possível alcançar a AWS. Confira a rede e a região."
        if "resourceconflictexception" in source:
            return "A função ainda está processando outra atualização. Aguarde e tente novamente."
        return str(self)


class AwsCliExecutor:
    """Executa a AWS CLI sem passar argumentos por um shell."""

    def __init__(self, binary: str | None = None, timeout_seconds: int = 120) -> None:
        self.binary = binary or find_aws_binary()
        self.timeout_seconds = timeout_seconds

    @property
    def available(self) -> bool:
        return bool(self.binary)

    def version(self) -> str:
        if not self.binary:
            raise AwsCliError("AWS CLI não encontrada no PATH.")
        completed = subprocess.run(
            [self.binary, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
            shell=False,
        )
        output = (completed.stdout or completed.stderr).strip()
        if completed.returncode != 0:
            raise AwsCliError(output or "Não foi possível executar a AWS CLI.")
        return output

    def _execute(
        self,
        command: AwsCommand,
        *,
        timeout_seconds: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if not self.binary:
            raise AwsCliError(
                "AWS CLI não encontrada no PATH.",
                command=command,
            )

        timeout = timeout_seconds or self.timeout_seconds
        try:
            completed = subprocess.run(
                [self.binary, *command.arguments],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as error:
            raise AwsCliError(
                f"A AWS CLI excedeu o limite de {timeout} segundos.",
                command=command,
            ) from error
        except OSError as error:
            raise AwsCliError(
                f"Falha ao iniciar a AWS CLI: {error}",
                command=command,
            ) from error

        if completed.returncode != 0:
            detail = completed.stderr.strip()
            raise AwsCliError(
                detail or "A AWS CLI encerrou com erro.",
                command=command,
                return_code=completed.returncode,
                stderr=detail,
            )

        return completed

    def run_text(
        self,
        command: AwsCommand,
        *,
        timeout_seconds: int | None = None,
    ) -> str:
        completed = self._execute(command, timeout_seconds=timeout_seconds)
        return completed.stdout.strip()

    def run_json(self, command: AwsCommand) -> dict[str, Any]:
        completed = self._execute(command)

        output = completed.stdout.strip()
        if not output:
            return {}
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError as error:
            raise AwsCliError(
                "A AWS CLI retornou uma resposta que não é JSON válido.",
                command=command,
                stderr=output[:500],
            ) from error
        if not isinstance(parsed, dict):
            raise AwsCliError(
                "A AWS CLI retornou um formato de resposta inesperado.",
                command=command,
            )
        return parsed


def find_aws_binary() -> str | None:
    """Localiza a AWS CLI inclusive logo após uma instalação no Windows."""

    configured = os.environ.get("PABLIN_AWS_BINARY") or os.environ.get(
        "EASYAWS_AWS_BINARY"
    )
    if configured:
        return configured

    from_path = shutil.which("aws")
    if from_path:
        return from_path

    candidates = [
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Programs"
        / "Amazon"
        / "AWSCLIV2"
        / "aws.exe",
        Path(os.environ.get("ProgramFiles", ""))
        / "Amazon"
        / "AWSCLIV2"
        / "aws.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


class DemoAwsCliExecutor:
    """Conta simulada para experimentar a interface sem acessar a AWS."""

    def __init__(self) -> None:
        self.identity: dict[str, str] = {
            "UserId": "AIDADEMOEXAMPLE",
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:user/demo-user",
        }
        self.functions: list[dict[str, object]] = [
            {
                "FunctionName": "processar-pedidos",
                "Runtime": "python3.13",
                "MemorySize": 256,
                "Timeout": 30,
                "LastModified": "2026-08-14T18:22:00+0000",
            },
            {
                "FunctionName": "upload-imagens",
                "Runtime": "nodejs22.x",
                "MemorySize": 512,
                "Timeout": 60,
                "LastModified": "2026-08-12T13:05:00+0000",
            },
            {
                "FunctionName": "enviar-email",
                "Runtime": "python3.13",
                "MemorySize": 128,
                "Timeout": 15,
                "LastModified": "2026-08-10T09:40:00+0000",
            },
        ]

    def run_json(self, command: AwsCommand) -> dict[str, Any]:
        arguments = command.arguments
        if arguments[:2] == ("sts", "get-caller-identity"):
            return dict(self.identity)
        if arguments[:2] == ("lambda", "list-functions"):
            return {"Functions": [dict(item) for item in self.functions]}
        if arguments[:2] == ("lambda", "update-function-configuration"):
            name = arguments[arguments.index("--function-name") + 1]
            memory = int(arguments[arguments.index("--memory-size") + 1])
            for function in self.functions:
                if function["FunctionName"] == name:
                    function["MemorySize"] = memory
                    return dict(function)
            raise AwsCliError(f"A função de demonstração `{name}` não existe.")
        raise AwsCliError("O modo de demonstração não implementa esse comando.")

    def run_text(
        self,
        command: AwsCommand,
        *,
        timeout_seconds: int | None = None,
    ) -> str:
        del timeout_seconds
        arguments = command.arguments
        if "--generate-cli-skeleton" in arguments:
            service, operation = arguments[:2]
            examples: dict[tuple[str, str], dict[str, object]] = {
                ("ec2", "describe-instances"): {"InstanceIds": [], "Filters": []},
                ("s3api", "create-bucket"): {
                    "Bucket": "nome-do-bucket",
                    "CreateBucketConfiguration": {"LocationConstraint": "sa-east-1"},
                },
                ("sqs", "send-message"): {
                    "QueueUrl": "https://sqs.sa-east-1.amazonaws.com/123456789012/fila",
                    "MessageBody": "mensagem",
                },
            }
            return json.dumps(examples.get((service, operation), {}), indent=2)
        if arguments and arguments[0] in {"logout", "configure"}:
            return ""
        if arguments and arguments[0] == "login":
            self.identity = {
                "UserId": "AIDADEMOSECOND",
                "Account": "999999999999",
                "Arn": "arn:aws:iam::999999999999:user/outra-conta-demo",
            }
            return "Perfil de demonstração atualizado."
        if len(arguments) >= 2:
            return json.dumps(
                {
                    "Demo": True,
                    "Service": arguments[0],
                    "Operation": arguments[1],
                    "Message": "Nenhuma chamada real foi enviada à AWS.",
                },
                indent=2,
                ensure_ascii=False,
            )
        raise AwsCliError("O modo de demonstração não implementa esse comando.")
