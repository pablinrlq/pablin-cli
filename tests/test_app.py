from __future__ import annotations

import asyncio

from textual.widgets import Button, DataTable, Input, OptionList, Static

from easyaws.app import build_app
from easyaws.aws_cli import DemoAwsCliExecutor
from easyaws.universal_screen import UniversalScreen


def test_demo_flow_lists_reviews_and_updates_a_function() -> None:
    async def scenario() -> None:
        executor = DemoAwsCliExecutor()
        app = build_app(executor=executor, demo=True)

        async with app.run_test(size=(130, 42)) as pilot:
            await pilot.click("#list-functions")
            await pilot.pause()

            table = app.query_one("#functions-table", DataTable)
            assert table.row_count == 3

            table.move_cursor(row=0)
            await pilot.pause()
            memory = app.query_one("#memory-input", Input)
            assert memory.disabled is False
            memory.value = "256"

            prepare = app.query_one("#prepare-update", Button)
            prepare.scroll_visible(animate=False)
            await pilot.pause()
            prepare.press()
            await pilot.pause()
            assert app.query_one("#confirm-update", Button).disabled is False
            assert app.pending_command is not None
            assert app.pending_command.mutates is True

            confirm = app.query_one("#confirm-update", Button)
            confirm.scroll_visible(animate=False)
            await pilot.pause()
            confirm.press()
            await pilot.pause()

            changed = next(
                item for item in executor.functions if item["FunctionName"] == "enviar-email"
            )
            assert changed["MemorySize"] == 256

    asyncio.run(scenario())


def test_account_panel_identifies_and_switches_demo_account() -> None:
    async def scenario() -> None:
        executor = DemoAwsCliExecutor()
        app = build_app(executor=executor, demo=True)

        async with app.run_test(size=(130, 42)) as pilot:
            await pilot.pause()
            info = app.query_one("#account-info", Static)
            assert "123456789012" in str(info.render())

            await pilot.click("#change-account")
            assert app.query_one("#switch-warning", Static).display is True

            confirm = app.query_one("#confirm-switch", Button)
            confirm.scroll_visible(animate=False)
            await pilot.pause()
            await pilot.click(confirm)
            await pilot.pause()

            assert executor.identity["Account"] == "999999999999"
            assert "999999999999" in str(info.render())

    asyncio.run(scenario())


def test_opens_catalog_with_all_demo_services() -> None:
    async def scenario() -> None:
        app = build_app(executor=DemoAwsCliExecutor(), demo=True)

        async with app.run_test(size=(150, 46)) as pilot:
            all_services = app.query_one("#all-services", Button)
            all_services.scroll_visible(animate=False)
            await pilot.pause()
            await pilot.click(all_services)
            await pilot.pause()

            assert isinstance(app.screen, UniversalScreen)
            assert app.screen.query_one("#catalog-services", OptionList).option_count == 16

    asyncio.run(scenario())


def test_service_shortcuts_are_enabled_and_open_the_selected_catalog() -> None:
    async def scenario() -> None:
        app = build_app(executor=DemoAwsCliExecutor(), demo=True)

        async with app.run_test(size=(150, 46)) as pilot:
            shortcuts = app.query(".catalog-service").results(Button)
            shortcut_names = {button.name for button in shortcuts}
            assert shortcut_names == {
                "cloudformation",
                "cloudwatch",
                "dynamodb",
                "ec2",
                "ecs",
                "eks",
                "iam",
                "logs",
                "rds",
                "route53",
                "s3api",
                "secretsmanager",
                "sns",
                "sqs",
            }
            assert all("em breve" not in str(button.label).casefold() for button in shortcuts)

            ec2 = app.query_one("#service-ec2", Button)
            assert ec2.disabled is False

            ec2.scroll_visible(animate=False)
            await pilot.pause()
            await pilot.click(ec2)
            await pilot.pause()

            assert isinstance(app.screen, UniversalScreen)
            assert app.screen.selected_service == "ec2"
            assert app.screen.query_one("#catalog-operations", OptionList).option_count == 5

    asyncio.run(scenario())
