"""Ponto de entrada compatível do Pablin CLI."""

from __future__ import annotations

import argparse

from . import __version__
from .aws_cli import AwsCliError, AwsCliExecutor, DemoAwsCliExecutor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pablin",
        description="Interface visual e guiada para a AWS CLI.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="abre uma conta simulada, sem executar comandos AWS",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="confere se a AWS CLI está disponível",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    executor = DemoAwsCliExecutor() if arguments.demo else AwsCliExecutor()

    if arguments.check:
        if arguments.demo:
            print("Modo de demonstração pronto; nenhuma conexão AWS será feita.")
            return
        try:
            print(f"AWS CLI encontrada: {executor.version()}")
        except AwsCliError as error:
            raise SystemExit(f"Pablin CLI: {error.friendly_message}") from error
        return

    from .app import build_app

    build_app(executor=executor, demo=arguments.demo).run()


if __name__ == "__main__":
    main()
