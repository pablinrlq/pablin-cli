"""Tela universal que navega pelo catálogo completo da AWS CLI."""

from __future__ import annotations

import asyncio
import webbrowser
from collections.abc import Callable

from rich.markup import escape
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    OptionList,
    Static,
    TextArea,
)
from textual.widgets.option_list import Option

from .aws_cli import AwsCliError, AwsCommand, CommandExecutor
from .catalog import AwsCliCatalog
from .models import AwsContext
from .universal_service import RiskLevel, UniversalAwsService, classify_operation


class UniversalScreen(Screen[None]):
    """Explorador gerado a partir da AWS CLI instalada."""

    TITLE = "Pablin CLI · Todos os serviços"

    CSS = """
    UniversalScreen {
        background: #07111f;
        color: #e6edf7;
    }

    #universal-shell {
        height: 1fr;
        padding: 1;
    }

    #universal-context {
        height: 2;
        color: #8dd7ff;
    }

    #catalog-columns {
        height: 1fr;
    }

    .catalog-column {
        width: 27;
        min-width: 20;
        border: round #263b53;
        padding: 0 1;
        margin-right: 1;
    }

    .catalog-column Label {
        height: 2;
        text-style: bold;
        color: #ffb547;
    }

    .catalog-search {
        margin-bottom: 1;
    }

    .catalog-list {
        height: 1fr;
    }

    #operation-panel {
        width: 1fr;
        border: round #2f638c;
        padding: 0 1;
    }

    #operation-title {
        height: 2;
        text-style: bold;
        color: #ffb547;
    }

    #operation-meta {
        min-height: 2;
        color: #8ca0b8;
        margin-bottom: 1;
    }

    #catalog-loading {
        height: 3;
        display: none;
    }

    #json-editor {
        height: 14;
        border: tall #263b53;
        margin-bottom: 1;
    }

    #extra-arguments {
        margin-bottom: 1;
    }

    #universal-actions {
        height: 3;
        margin-bottom: 1;
    }

    #universal-actions Button {
        margin-right: 1;
    }

    #universal-preview {
        min-height: 5;
        border: round #ffb547;
        padding: 1;
        margin-bottom: 1;
        color: #ffd28a;
    }

    #confirmation-phrase {
        display: none;
        margin-bottom: 1;
    }

    #run-operation {
        display: none;
        width: 36;
        margin-bottom: 1;
    }

    #operation-output {
        min-height: 5;
        border: round #2f638c;
        padding: 1;
        color: #b7e4ff;
    }
    """

    BINDINGS = [
        ("escape", "back", "Voltar"),
        ("ctrl+p", "focus_service_search", "Pesquisar serviço"),
    ]

    def __init__(
        self,
        executor: CommandExecutor,
        catalog: AwsCliCatalog,
        context_provider: Callable[[], AwsContext],
        initial_service: str | None = None,
    ) -> None:
        super().__init__()
        self.executor = executor
        self.catalog = catalog
        self.context_provider = context_provider
        self.universal = UniversalAwsService(executor)
        self.initial_service = initial_service
        self.services: list[str] = []
        self.operations: list[str] = []
        self.selected_service: str | None = None
        self.selected_operation: str | None = None
        self.pending_command: AwsCommand | None = None
        self.expected_confirmation = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="universal-shell"):
            context = self.context_provider()
            yield Static(
                f"Perfil [b]{context.profile}[/b] · região [b]{context.region}[/b] · "
                "catálogo da AWS CLI instalada",
                id="universal-context",
            )
            with Horizontal(id="catalog-columns"):
                with Vertical(classes="catalog-column"):
                    yield Label("1. Serviço")
                    yield Input(
                        placeholder="Pesquisar entre todos...",
                        id="catalog-service-search",
                        classes="catalog-search",
                    )
                    yield OptionList(id="catalog-services", classes="catalog-list")
                with Vertical(classes="catalog-column"):
                    yield Label("2. Operação")
                    yield Input(
                        placeholder="Pesquisar operação...",
                        id="catalog-operation-search",
                        classes="catalog-search",
                    )
                    yield OptionList(id="catalog-operations", classes="catalog-list")
                with VerticalScroll(id="operation-panel"):
                    yield Static("Escolha um serviço e uma operação", id="operation-title")
                    yield Static(
                        "O Pablin CLI classificará o risco antes de liberar a execução.",
                        id="operation-meta",
                    )
                    yield LoadingIndicator(id="catalog-loading")
                    yield TextArea(
                        "{}",
                        language="json",
                        theme="dracula",
                        show_line_numbers=True,
                        id="json-editor",
                    )
                    yield Input(
                        placeholder="Argumentos extras opcionais, ex.: caminho-do-arquivo",
                        id="extra-arguments",
                    )
                    with Horizontal(id="universal-actions"):
                        yield Button(
                            "Gerar formulário AWS",
                            id="generate-skeleton",
                            disabled=True,
                        )
                        yield Button(
                            "Revisar comando",
                            id="review-operation",
                            disabled=True,
                            variant="primary",
                        )
                        yield Button(
                            "Documentação oficial",
                            id="open-documentation",
                            disabled=True,
                        )
                        yield Button("Voltar", id="back-universal")
                    yield Static(
                        "O comando completo aparecerá aqui.",
                        id="universal-preview",
                    )
                    yield Input(id="confirmation-phrase")
                    yield Button(
                        "Executar",
                        id="run-operation",
                        disabled=True,
                        variant="error",
                    )
                    yield Static("Nenhuma operação executada.", id="operation-output")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#catalog-service-search", Input).focus()
        self.run_worker(self.load_services(), exclusive=True, group="catalog")

    def set_loading(self, loading: bool) -> None:
        self.query_one("#catalog-loading", LoadingIndicator).display = loading

    def populate_options(self, selector: str, values: list[str]) -> None:
        options = self.query_one(selector, OptionList)
        options.clear_options()
        options.add_options(Option(value, id=value) for value in values)

    async def load_services(self) -> None:
        self.set_loading(True)
        try:
            self.services = await asyncio.to_thread(self.catalog.list_services)
        except (AwsCliError, ValueError) as error:
            self.notify(str(error), title="Catálogo AWS", severity="error", timeout=8)
        else:
            self.populate_options("#catalog-services", self.services)
            self.query_one("#operation-meta", Static).update(
                f"{len(self.services)} serviços descobertos na AWS CLI instalada."
            )
            if self.initial_service in self.services:
                service_list = self.query_one("#catalog-services", OptionList)
                service_list.highlighted = self.services.index(self.initial_service)
                self.selected_service = self.initial_service
                await self.load_operations(self.initial_service)
        finally:
            self.set_loading(False)

    async def load_operations(self, service: str) -> None:
        self.set_loading(True)
        try:
            self.operations = await asyncio.to_thread(
                self.catalog.list_operations,
                service,
            )
        except (AwsCliError, ValueError) as error:
            self.notify(str(error), title="Operações AWS", severity="error", timeout=8)
        else:
            self.populate_options("#catalog-operations", self.operations)
            self.query_one("#operation-title", Static).update(service)
            self.query_one("#operation-meta", Static).update(
                f"{len(self.operations)} operações disponíveis. Escolha uma para continuar."
            )
        finally:
            self.set_loading(False)

    def invalidate_review(self) -> None:
        self.pending_command = None
        self.expected_confirmation = ""
        for button in self.query("#run-operation").results(Button):
            button.disabled = True
            button.display = False
        for field in self.query("#confirmation-phrase").results(Input):
            field.display = False
            field.value = ""

    @on(Input.Changed, "#catalog-service-search")
    def filter_services(self, event: Input.Changed) -> None:
        query = event.value.strip().casefold()
        filtered = [value for value in self.services if query in value.casefold()]
        self.populate_options("#catalog-services", filtered)

    @on(Input.Changed, "#catalog-operation-search")
    def filter_operations(self, event: Input.Changed) -> None:
        query = event.value.strip().casefold()
        filtered = [value for value in self.operations if query in value.casefold()]
        self.populate_options("#catalog-operations", filtered)

    @on(OptionList.OptionSelected, "#catalog-services")
    def select_service(self, event: OptionList.OptionSelected) -> None:
        if not event.option.id:
            return
        self.selected_service = event.option.id
        self.selected_operation = None
        self.operations = []
        self.populate_options("#catalog-operations", [])
        self.invalidate_review()
        self.run_worker(
            self.load_operations(self.selected_service),
            exclusive=True,
            group="operations",
        )

    @on(OptionList.OptionSelected, "#catalog-operations")
    async def select_operation(self, event: OptionList.OptionSelected) -> None:
        if not event.option.id or not self.selected_service:
            return
        self.selected_operation = event.option.id
        self.invalidate_review()
        risk = classify_operation(self.selected_operation)
        self.query_one("#operation-title", Static).update(
            f"{self.selected_service} · {self.selected_operation}"
        )
        self.set_loading(True)
        try:
            parameters = await asyncio.to_thread(
                self.catalog.list_parameters,
                self.selected_service,
                self.selected_operation,
            )
        except (AwsCliError, ValueError):
            parameters = []
        finally:
            self.set_loading(False)
        self.query_one("#operation-meta", Static).update(
            f"Risco: [b]{risk.value}[/b] · {len(parameters)} parâmetros reconhecidos."
        )
        self.query_one("#generate-skeleton", Button).disabled = False
        self.query_one("#review-operation", Button).disabled = False
        self.query_one("#open-documentation", Button).disabled = False

    @on(Button.Pressed, "#open-documentation")
    def open_documentation(self) -> None:
        if not self.selected_service or not self.selected_operation:
            return
        url = (
            "https://docs.aws.amazon.com/cli/latest/reference/"
            f"{self.selected_service}/{self.selected_operation}.html"
        )
        if not webbrowser.open(url):
            self.notify(url, title="Abra esta documentação", severity="warning")

    @on(Button.Pressed, "#generate-skeleton")
    async def generate_skeleton(self) -> None:
        if not self.selected_service or not self.selected_operation:
            return
        self.set_loading(True)
        try:
            skeleton = await asyncio.to_thread(
                self.universal.input_skeleton,
                self.selected_service,
                self.selected_operation,
            )
        except AwsCliError as error:
            self.notify(
                error.friendly_message,
                title="Formulário indisponível",
                severity="warning",
            )
            skeleton = "{}"
        finally:
            self.set_loading(False)
        self.query_one("#json-editor", TextArea).load_text(skeleton)
        self.invalidate_review()

    @on(Button.Pressed, "#review-operation")
    def review_operation(self) -> None:
        if not self.selected_service or not self.selected_operation:
            return
        try:
            command = self.universal.build_command(
                self.context_provider(),
                self.selected_service,
                self.selected_operation,
                self.query_one("#json-editor", TextArea).text,
                self.query_one("#extra-arguments", Input).value,
            )
        except ValueError as error:
            self.notify(str(error), title="Não foi possível revisar", severity="error")
            return

        risk = classify_operation(self.selected_operation)
        self.pending_command = command
        self.query_one("#universal-preview", Static).update(
            f"[b]Risco:[/b] {risk.value}\n[b]Comando:[/b]\n$ {escape(command.display())}"
        )
        run_button = self.query_one("#run-operation", Button)
        run_button.display = True
        confirmation = self.query_one("#confirmation-phrase", Input)
        if risk is RiskLevel.READ_ONLY:
            self.expected_confirmation = ""
            confirmation.display = False
            run_button.label = "Executar operação de leitura"
            run_button.variant = "success"
            run_button.disabled = False
        else:
            self.expected_confirmation = (
                "EXCLUIR" if risk is RiskLevel.DESTRUCTIVE else "CONFIRMAR"
            )
            confirmation.placeholder = (
                f"Digite {self.expected_confirmation} para liberar a operação"
            )
            confirmation.display = True
            confirmation.value = ""
            run_button.label = "Confirmar e executar"
            run_button.variant = "error"
            run_button.disabled = True

    @on(Input.Changed, "#confirmation-phrase")
    def check_confirmation(self, event: Input.Changed) -> None:
        if self.pending_command is None:
            return
        self.query_one("#run-operation", Button).disabled = (
            event.value.strip() != self.expected_confirmation
        )

    @on(TextArea.Changed, "#json-editor")
    @on(Input.Changed, "#extra-arguments")
    def input_changed(self) -> None:
        self.invalidate_review()

    @on(Button.Pressed, "#run-operation")
    async def run_operation(self) -> None:
        command = self.pending_command
        if command is None or not self.selected_service or not self.selected_operation:
            return
        try:
            rebuilt = self.universal.build_command(
                self.context_provider(),
                self.selected_service,
                self.selected_operation,
                self.query_one("#json-editor", TextArea).text,
                self.query_one("#extra-arguments", Input).value,
            )
        except ValueError as error:
            self.invalidate_review()
            self.notify(str(error), severity="error")
            return
        if rebuilt != command:
            self.invalidate_review()
            self.notify("Os dados mudaram. Revise o comando novamente.", severity="warning")
            return

        self.set_loading(True)
        self.query_one("#run-operation", Button).disabled = True
        try:
            output = await asyncio.to_thread(self.universal.execute, command)
        except AwsCliError as error:
            self.query_one("#operation-output", Static).update(
                f"[b]Erro:[/b] {escape(error.friendly_message)}"
            )
            self.notify(error.friendly_message, severity="error", timeout=10)
        else:
            visible_output = output if len(output) <= 20_000 else output[:20_000] + "\n… saída truncada"
            self.query_one("#operation-output", Static).update(
                escape(visible_output or "Operação concluída sem conteúdo de resposta.")
            )
            self.notify("Operação concluída.", title="AWS CLI")
        finally:
            self.set_loading(False)
            self.invalidate_review()

    @on(Button.Pressed, "#back-universal")
    def handle_back(self) -> None:
        self.app.pop_screen()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_focus_service_search(self) -> None:
        self.query_one("#catalog-service-search", Input).focus()
