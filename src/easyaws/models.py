"""Modelos compartilhados pelo núcleo e pela interface."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AwsContext:
    """Contexto explícito usado em todas as chamadas para a AWS."""

    region: str
    profile: str | None = None

    def global_arguments(self) -> tuple[str, ...]:
        arguments: list[str] = ["--region", self.region]
        if self.profile:
            arguments.extend(("--profile", self.profile))
        arguments.extend(("--output", "json", "--no-cli-pager"))
        return tuple(arguments)


@dataclass(frozen=True, slots=True)
class AwsIdentity:
    """Identidade retornada pelo AWS STS para o perfil selecionado."""

    account_id: str
    arn: str
    user_id: str

    @property
    def principal(self) -> str:
        return self.arn.rsplit("/", 1)[-1]


@dataclass(frozen=True, slots=True)
class LambdaFunction:
    """Parte da configuração de uma Lambda relevante para o MVP."""

    name: str
    runtime: str
    memory_size: int
    timeout: int
    last_modified: str

    @classmethod
    def from_aws(cls, value: dict[str, object]) -> "LambdaFunction":
        return cls(
            name=str(value.get("FunctionName", "")),
            runtime=str(value.get("Runtime") or "imagem"),
            memory_size=int(value.get("MemorySize", 0)),
            timeout=int(value.get("Timeout", 0)),
            last_modified=str(value.get("LastModified", "")),
        )
