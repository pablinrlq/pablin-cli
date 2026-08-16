"""Interface visual do Pablin CLI construída com Textual."""

from __future__ import annotations

import asyncio

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    Select,
    Static,
)

from .account_service import AccountService
from .aws_cli import AwsCliError, AwsCliExecutor, AwsCommand, CommandExecutor
from .catalog import AwsCliCatalog, DemoAwsCliCatalog
from .config import default_profile, default_region, discover_profiles
from .lambda_service import LambdaService
from .models import AwsContext, LambdaFunction
from .universal_screen import UniversalScreen


QUICK_SERVICES = (
    ("EC2", "ec2"),
    ("S3", "s3api"),
    ("IAM", "iam"),
    ("RDS", "rds"),
    ("DynamoDB", "dynamodb"),
    ("CloudWatch", "cloudwatch"),
    ("CloudWatch Logs", "logs"),
    ("ECS", "ecs"),
    ("EKS", "eks"),
    ("CloudFormation", "cloudformation"),
    ("SQS", "sqs"),
    ("SNS", "sns"),
    ("Route 53", "route53"),
    ("Secrets Manager", "secretsmanager"),
)


class PablinApp(App[None]):
    """Console AWS guiado dentro do terminal."""

    TITLE = "Pablin CLI"
    SUB_TITLE = "AWS CLI, só que guiada"

    CSS = """
    Screen {
        background: #07111f;
        color: #e6edf7;
    }

    Header {
        background: #0d1b2d;
        color: #ffb547;
    }

    #shell {
        height: 1fr;
        padding: 1 2;
    }

    #brand {
        height: 3;
        content-align: left middle;
        color: #ffb547;
        text-style: bold;
    }

    #tagline {
        height: 2;
        color: #8ca0b8;
    }

    #context-row {
        height: 5;
        padding: 0 0 1 0;
    }

    .context-field {
        width: 1fr;
        margin-right: 2;
    }

    .context-field Label {
        height: 1;
        color: #8ca0b8;
    }

    #body {
        height: 1fr;
        min-height: 24;
    }

    #account-panel {
        height: auto;
        border: round #2f638c;
        padding: 0 1;
        margin-bottom: 1;
    }

    #account-info {
        height: 2;
        color: #8dd7ff;
    }

    #account-actions, #switch-actions {
        height: 3;
    }

    #account-actions Button, #switch-actions Button {
        margin-right: 1;
    }

    #switch-warning {
        height: 3;
        color: #ffd28a;
        display: none;
    }

    #switch-actions {
        display: none;
    }

    #services {
        width: 31;
        min-width: 25;
        border: round #263b53;
        padding: 1;
        margin-right: 1;
    }

    #services-title, #lambda-title {
        height: 2;
        text-style: bold;
    }

    #service-search {
        margin-bottom: 1;
    }

    .service-button {
        width: 100%;
        margin-bottom: 1;
    }

    #lambda-service {
        background: #ff9900;
        color: #101820;
        text-style: bold;
    }

    #workspace {
        width: 1fr;
        border: round #263b53;
        padding: 1 2;
    }

    #workspace-intro {
        color: #8ca0b8;
        margin-bottom: 1;
    }

    #actions {
        height: 3;
        margin-bottom: 1;
    }

    #actions Button {
        margin-right: 1;
    }

    #loading {
        height: 3;
        display: none;
    }

    #functions-table {
        height: 12;
        border: tall #263b53;
        margin-bottom: 1;
    }

    #selection {
        height: 2;
        color: #57d3a6;
    }

    #memory-row {
        height: 4;
    }

    #memory-input {
        width: 18;
        margin-right: 1;
    }

    #preview {
        min-height: 5;
        border: round #ffb547;
        padding: 1;
        margin-bottom: 1;
        color: #ffd28a;
    }

    #confirm-update {
        width: 32;
        background: #d97706;
    }

    #mode-badge {
        dock: right;
        width: auto;
        padding: 0 1;
        background: #15334f;
        color: #8dd7ff;
    }

    Footer {
        background: #0d1b2d;
    }
    """

    BINDINGS = [
        ("q", "quit", "Sair"),
        ("r", "refresh", "Atualizar Lambdas"),
        ("ctrl+p", "focus_search", "Pesquisar serviço"),
    ]

    def __init__(self, executor: CommandExecutor | None = None, *, demo: bool = False) -> None:
        super().__init__()
        self.executor = executor or AwsCliExecutor()
        self.demo = demo
        self.account_service = AccountService(self.executor)
        self.lambda_service = LambdaService(self.executor)
        self.catalog = DemoAwsCliCatalog() if demo else AwsCliCatalog()
        self.profiles = ["demo"] if demo else discover_profiles()
        self.initial_profile = self.profiles[0] if demo else default_profile(self.profiles)
        self.initial_region = "sa-east-1" if demo else default_region(self.initial_profile)
        self.functions: dict[str, LambdaFunction] = {}
        self.selected_function: str | None = None
        self.pending_command: AwsCommand | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll(id="shell"):
            yield Static("PABLIN CLI", id="brand")
            yield Static(
                "Encontre o recurso, revise a operação e só então execute.",
                id="tagline",
            )
            yield Static("DEMONSTRAÇÃO" if self.demo else "CONTA REAL", id="mode-badge")
            with Horizontal(id="context-row"):
                with Vertical(classes="context-field"):
                    yield Label("Perfil AWS")
                    yield Select(
                        [(profile, profile) for profile in self.profiles],
                        value=self.initial_profile,
                        allow_blank=False,
                        id="profile-select",
                    )
                with Vertical(classes="context-field"):
                    yield Label("Região")
                    yield Input(value=self.initial_region, id="region-input")
            with Vertical(id="account-panel"):
                yield Static("Verificando a conta conectada...", id="account-info")
                with Horizontal(id="account-actions"):
                    yield Button("Atualizar identificação", id="refresh-account")
                    yield Button(
                        "Entrar em outra conta",
                        id="change-account",
                        variant="warning",
                    )
                yield Static(
                    "A troca encerra a sessão e remove credenciais somente deste perfil. "
                    "Os demais perfis não serão alterados.",
                    id="switch-warning",
                )
                with Horizontal(id="switch-actions"):
                    yield Button("Cancelar", id="cancel-switch")
                    yield Button(
                        "Confirmar, sair e fazer novo login",
                        id="confirm-switch",
                        variant="error",
                    )
            with Horizontal(id="body"):
                with VerticalScroll(id="services"):
                    yield Static("Serviços", id="services-title")
                    yield Input(placeholder="Pesquisar serviço...", id="service-search")
                    yield Button(
                        "◎  Todos os serviços",
                        id="all-services",
                        classes="service-button",
                        variant="primary",
                    )
                    yield Button("λ  Lambda", id="lambda-service", classes="service-button")
                    for label, service in QUICK_SERVICES:
                        yield Button(
                            label,
                            id=f"service-{service}",
                            name=service,
                            classes="service-button catalog-service",
                        )
                with VerticalScroll(id="workspace"):
                    yield Static("Lambda", id="lambda-title")
                    yield Static(
                        "Liste funções existentes, selecione uma e prepare uma alteração segura.",
                        id="workspace-intro",
                    )
                    with Horizontal(id="actions"):
                        yield Button("Listar funções", id="list-functions", variant="primary")
                    yield LoadingIndicator(id="loading")
                    yield DataTable(id="functions-table")
                    yield Static("Nenhuma função selecionada.", id="selection")
                    with Horizontal(id="memory-row"):
                        yield Input(
                            placeholder="Nova memória em MB",
                            type="integer",
                            disabled=True,
                            id="memory-input",
                        )
                        yield Button(
                            "Revisar alteração",
                            id="prepare-update",
                            disabled=True,
                        )
                    yield Static(
                        "O comando AWS aparecerá aqui antes de qualquer alteração.",
                        id="preview",
                    )
                    yield Button(
                        "Confirmar e executar",
                        id="confirm-update",
                        disabled=True,
                    )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#functions-table", DataTable)
        table.add_columns("Função", "Runtime", "Memória", "Timeout", "Última alteração")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.query_one("#change-account", Button).focus()
        self.run_worker(self.refresh_identity(), exclusive=True, group="account")

    def current_context(self) -> AwsContext:
        profile_value = self.query_one("#profile-select", Select).value
        profile = None if profile_value is Select.BLANK else str(profile_value)
        region = self.query_one("#region-input", Input).value.strip()
        return AwsContext(profile=profile, region=region)

    def invalidate_preview(self) -> None:
        self.pending_command = None
        for button in self.query("#confirm-update").results(Button):
            button.disabled = True
        for preview in self.query("#preview").results(Static):
            preview.update("O comando AWS aparecerá aqui antes de qualquer alteração.")

    def set_busy(self, busy: bool) -> None:
        self.query_one("#loading", LoadingIndicator).display = busy
        self.query_one("#list-functions", Button).disabled = busy
        if busy:
            self.query_one("#confirm-update", Button).disabled = True

    def show_switch_confirmation(self, visible: bool) -> None:
        self.query_one("#switch-warning", Static).display = visible
        self.query_one("#switch-actions", Horizontal).display = visible
        self.query_one("#account-actions", Horizontal).display = not visible

    async def refresh_identity(self) -> None:
        info = self.query_one("#account-info", Static)
        info.update("Verificando a conta conectada...")
        try:
            identity = await asyncio.to_thread(
                self.account_service.get_identity,
                self.current_context(),
            )
        except (AwsCliError, ValueError) as error:
            message = error.friendly_message if isinstance(error, AwsCliError) else str(error)
            info.update(f"[b]Nenhuma sessão válida neste perfil.[/b] {message}")
            self.query_one("#change-account", Button).label = "Fazer login"
            return

        context = self.current_context()
        info.update(
            f"[b]Conta {identity.account_id}[/b] · {identity.principal}\n"
            f"{identity.arn} · perfil {context.profile} · região {context.region}"
        )
        self.query_one("#change-account", Button).label = "Entrar em outra conta"

    @on(Button.Pressed, "#refresh-account")
    async def handle_refresh_account(self) -> None:
        await self.refresh_identity()

    @on(Button.Pressed, "#change-account")
    def handle_change_account(self) -> None:
        self.show_switch_confirmation(True)

    @on(Button.Pressed, "#cancel-switch")
    def handle_cancel_switch(self) -> None:
        self.show_switch_confirmation(False)

    @on(Button.Pressed, "#confirm-switch")
    async def handle_confirm_switch(self) -> None:
        context = self.current_context()
        button = self.query_one("#confirm-switch", Button)
        button.disabled = True
        self.query_one("#account-info", Static).update(
            "Encerrando a sessão anterior. Conclua o novo login no navegador..."
        )
        try:
            identity = await asyncio.to_thread(
                self.account_service.switch_account,
                context,
            )
        except (AwsCliError, ValueError) as error:
            message = error.friendly_message if isinstance(error, AwsCliError) else str(error)
            self.query_one("#account-info", Static).update(
                f"[b]O novo login não foi concluído.[/b] {message}"
            )
            self.notify(message, title="Troca de conta", severity="error", timeout=10)
        else:
            self.query_one("#account-info", Static).update(
                f"[b]Conta {identity.account_id}[/b] · {identity.principal}\n"
                f"{identity.arn} · perfil {context.profile} · região {context.region}"
            )
            self.functions.clear()
            self.query_one("#functions-table", DataTable).clear(columns=False)
            self.notify("Nova conta conectada com sucesso.", title="Conta AWS")
        finally:
            button.disabled = False
            self.show_switch_confirmation(False)

    async def load_functions(self) -> None:
        self.invalidate_preview()
        self.set_busy(True)
        try:
            functions = await asyncio.to_thread(
                self.lambda_service.list_functions,
                self.current_context(),
            )
        except (AwsCliError, ValueError) as error:
            message = error.friendly_message if isinstance(error, AwsCliError) else str(error)
            self.notify(message, title="Não foi possível listar", severity="error", timeout=8)
            return
        finally:
            self.set_busy(False)

        self.functions = {function.name: function for function in functions}
        self.selected_function = None
        table = self.query_one("#functions-table", DataTable)
        table.clear(columns=False)
        for function in functions:
            table.add_row(
                function.name,
                function.runtime,
                f"{function.memory_size} MB",
                f"{function.timeout} s",
                function.last_modified,
                key=function.name,
            )
        self.query_one("#memory-input", Input).disabled = True
        self.query_one("#prepare-update", Button).disabled = True
        self.query_one("#selection", Static).update(
            f"{len(functions)} função(ões) encontrada(s). Selecione uma linha."
            if functions
            else "Nenhuma função encontrada neste perfil e região."
        )
        self.notify(f"{len(functions)} função(ões) carregada(s).", title="Lambda")

    @on(Button.Pressed, "#list-functions")
    async def handle_list_functions(self) -> None:
        await self.load_functions()

    @on(Button.Pressed, "#lambda-service")
    def handle_lambda_service(self) -> None:
        self.query_one("#workspace", VerticalScroll).focus()

    @on(Button.Pressed, "#all-services")
    def handle_all_services(self) -> None:
        self.open_catalog()

    @on(Button.Pressed, ".catalog-service")
    def handle_catalog_service(self, event: Button.Pressed) -> None:
        self.open_catalog(event.button.name)

    def open_catalog(self, service: str | None = None) -> None:
        self.push_screen(
            UniversalScreen(
                executor=self.executor,
                catalog=self.catalog,
                context_provider=self.current_context,
                initial_service=service,
            )
        )

    @on(DataTable.RowHighlighted, "#functions-table")
    def handle_function_highlighted(self, event: DataTable.RowHighlighted) -> None:
        name = str(event.row_key.value)
        function = self.functions.get(name)
        if function is None:
            return
        self.selected_function = name
        memory_input = self.query_one("#memory-input", Input)
        memory_input.disabled = False
        memory_input.value = str(function.memory_size)
        self.query_one("#prepare-update", Button).disabled = False
        self.query_one("#selection", Static).update(
            f"Selecionada: [b]{name}[/b] · memória atual: {function.memory_size} MB"
        )
        self.invalidate_preview()

    @on(Button.Pressed, "#prepare-update")
    def handle_prepare_update(self) -> None:
        if not self.selected_function:
            self.notify("Selecione uma função primeiro.", severity="warning")
            return
        value = self.query_one("#memory-input", Input).value.strip()
        try:
            memory_size = int(value)
            command = self.lambda_service.memory_update_command(
                self.current_context(),
                self.selected_function,
                memory_size,
            )
        except ValueError as error:
            self.notify(str(error), title="Valor inválido", severity="error")
            return

        current = self.functions[self.selected_function]
        if current.memory_size == memory_size:
            self.notify("A função já usa essa quantidade de memória.", severity="warning")
            return

        self.pending_command = command
        self.query_one("#preview", Static).update(
            "[b]Resumo da alteração[/b]\n"
            f"Função: {current.name}\n"
            f"Região: {self.current_context().region}\n"
            f"Memória: {current.memory_size} MB → {memory_size} MB\n\n"
            f"[b]Comando:[/b]\n$ {command.display()}"
        )
        self.query_one("#confirm-update", Button).disabled = False

    @on(Button.Pressed, "#confirm-update")
    async def handle_confirm_update(self) -> None:
        command = self.pending_command
        if command is None or not self.selected_function:
            self.notify("Revise a alteração novamente.", severity="warning")
            return

        expected = self.lambda_service.memory_update_command(
            self.current_context(),
            self.selected_function,
            int(self.query_one("#memory-input", Input).value),
        )
        if command != expected:
            self.invalidate_preview()
            self.notify("Os dados mudaram. Revise o comando novamente.", severity="warning")
            return

        self.set_busy(True)
        try:
            await asyncio.to_thread(self.executor.run_json, command)
        except AwsCliError as error:
            self.notify(
                error.friendly_message,
                title="Alteração não executada",
                severity="error",
                timeout=8,
            )
            return
        finally:
            self.set_busy(False)

        self.notify("Memória atualizada com sucesso.", title="Lambda", severity="information")
        await self.load_functions()

    @on(Input.Changed, "#service-search")
    def handle_service_search(self, event: Input.Changed) -> None:
        query = event.value.strip().casefold()
        for button in self.query(".service-button").results(Button):
            button.display = not query or query in str(button.label).casefold()

    @on(Input.Changed, "#region-input")
    @on(Input.Changed, "#memory-input")
    def handle_relevant_input_change(self) -> None:
        self.invalidate_preview()

    @on(Select.Changed, "#profile-select")
    def handle_profile_change(self) -> None:
        self.invalidate_preview()
        if self.is_mounted:
            self.run_worker(self.refresh_identity(), exclusive=True, group="account")

    def action_refresh(self) -> None:
        self.run_worker(self.load_functions(), exclusive=True)

    def action_focus_search(self) -> None:
        self.query_one("#service-search", Input).focus()


def build_app(executor: CommandExecutor | None = None, *, demo: bool = False) -> PablinApp:
    return PablinApp(executor=executor, demo=demo)


# Compatibilidade para integrações que importavam o nome antigo.
EasyAWSApp = PablinApp
