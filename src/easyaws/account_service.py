"""Identificação da conta e troca segura da sessão local."""

from __future__ import annotations

from collections.abc import Callable

from .aws_cli import AwsCliError, AwsCommand, CommandExecutor
from .config import clear_profile_authentication
from .lambda_service import validate_context
from .models import AwsContext, AwsIdentity


class AccountService:
    """Consulta o STS e gerencia somente o perfil explicitamente selecionado."""

    def __init__(
        self,
        executor: CommandExecutor,
        credential_cleaner: Callable[[str], None] = clear_profile_authentication,
    ) -> None:
        self.executor = executor
        self.credential_cleaner = credential_cleaner

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

    def credential_source_command(self, profile: str) -> AwsCommand:
        return AwsCommand(
            arguments=("configure", "list", "--profile", profile),
            description=f"Verificar a origem das credenciais do perfil {profile}",
        )

    @staticmethod
    def _validate_login_source(output: str) -> None:
        credential_types: dict[str, str] = {}
        for line in output.splitlines():
            fields = [field.strip().lower() for field in line.split(":", 3)]
            if len(fields) == 4 and fields[0] in {"access_key", "secret_key"}:
                credential_types[fields[0]] = fields[2]
        if credential_types != {"access_key": "login", "secret_key": "login"}:
            raise AwsCliError(
                "O login terminou, mas a AWS CLI ainda não está usando credenciais "
                "do tipo login neste perfil."
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

        self.credential_cleaner(profile)
        self.executor.run_text(self.login_command(context), timeout_seconds=600)
        source = self.executor.run_text(self.credential_source_command(profile))
        self._validate_login_source(source)
        return self.get_identity(context)
