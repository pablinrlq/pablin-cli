"""Identificação da conta e troca segura da sessão local."""

from __future__ import annotations

from .aws_cli import AwsCliError, AwsCommand, CommandExecutor
from .lambda_service import validate_context
from .models import AwsContext, AwsIdentity


class AccountService:
    """Consulta o STS e gerencia somente o perfil explicitamente selecionado."""

    _CREDENTIAL_KEYS = (
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_session_token",
        "credential_process",
        "login_session",
    )

    def __init__(self, executor: CommandExecutor) -> None:
        self.executor = executor

    def identity_command(self, context: AwsContext) -> AwsCommand:
        validate_context(context)
        return AwsCommand(
            arguments=("sts", "get-caller-identity", *context.global_arguments()),
            description="Identificar a conta AWS conectada",
        )

    def get_identity(self, context: AwsContext) -> AwsIdentity:
        response = self.executor.run_json(self.identity_command(context))
        account_id = str(response.get("Account", ""))
        arn = str(response.get("Arn", ""))
        user_id = str(response.get("UserId", ""))
        if not account_id or not arn or not user_id:
            raise AwsCliError("A AWS retornou uma identidade incompleta.")
        return AwsIdentity(account_id=account_id, arn=arn, user_id=user_id)

    def logout_command(self, profile: str) -> AwsCommand:
        return AwsCommand(
            arguments=("logout", "--profile", profile, "--no-cli-pager"),
            description=f"Encerrar a sessão temporária do perfil {profile}",
            mutates=True,
        )

    def unset_command(self, profile: str, key: str) -> AwsCommand:
        if key not in self._CREDENTIAL_KEYS:
            raise ValueError("Chave de credencial não permitida para limpeza.")
        return AwsCommand(
            arguments=("configure", "unset", key, "--profile", profile),
            description=f"Remover {key} somente do perfil {profile}",
            mutates=True,
        )

    def login_command(self, context: AwsContext) -> AwsCommand:
        validate_context(context)
        if not context.profile:
            raise ValueError("Selecione um perfil antes de trocar de conta.")
        return AwsCommand(
            arguments=(
                "login",
                "--profile",
                context.profile,
                "--region",
                context.region,
                "--no-cli-pager",
            ),
            description=f"Entrar novamente no perfil {context.profile}",
            mutates=True,
        )

    def switch_account(self, context: AwsContext) -> AwsIdentity:
        """Remove credenciais do perfil escolhido e inicia um novo login."""

        validate_context(context)
        profile = context.profile
        if not profile:
            raise ValueError("Selecione um perfil antes de trocar de conta.")

        try:
            self.executor.run_text(self.logout_command(profile))
        except AwsCliError as error:
            detail = f"{error} {error.stderr}".lower()
            if "login" not in detail and "session" not in detail and "cache" not in detail:
                raise

        for key in self._CREDENTIAL_KEYS:
            self.executor.run_text(self.unset_command(profile, key))

        self.executor.run_text(self.login_command(context), timeout_seconds=600)
        return self.get_identity(context)
