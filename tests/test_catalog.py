from __future__ import annotations

import subprocess

from easyaws.catalog import AwsCliCatalog


def test_catalog_discovers_services_operations_and_parameters(monkeypatch) -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        line = kwargs["env"]["COMP_LINE"]  # type: ignore[index]
        outputs = {
            "aws ": "lambda\nec2\nconfigure\n--profile\n",
            "aws lambda ": "list-functions\ncreate-function\n--region\n",
            "aws lambda list-functions --": "--function-version\n--profile\n",
        }
        return subprocess.CompletedProcess(argv, 0, outputs[line], "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    catalog = AwsCliCatalog(completer="aws-completer-test")

    assert catalog.list_services() == ["ec2", "lambda"]
    assert catalog.list_operations("lambda") == ["create-function", "list-functions"]
    assert catalog.list_parameters("lambda", "list-functions") == [
        "--function-version",
        "--profile",
    ]

