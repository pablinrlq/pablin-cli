from __future__ import annotations

import pytest

from easyaws.aws_cli import DemoAwsCliExecutor
from easyaws.models import AwsContext
from easyaws.universal_service import (
    RiskLevel,
    UniversalAwsService,
    classify_operation,
)


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        ("describe-instances", RiskLevel.READ_ONLY),
        ("list-buckets", RiskLevel.READ_ONLY),
        ("create-function", RiskLevel.MUTATING),
        ("update-function-configuration", RiskLevel.MUTATING),
        ("delete-function", RiskLevel.DESTRUCTIVE),
        ("terminate-instances", RiskLevel.DESTRUCTIVE),
    ],
)
def test_classifies_operation_risk(operation: str, expected: RiskLevel) -> None:
    assert classify_operation(operation) is expected


@pytest.mark.parametrize(
    ("service_name", "operation", "expected"),
    [
        ("s3api", "get-object", RiskLevel.LOCAL_WRITE),
        ("secretsmanager", "get-secret-value", RiskLevel.SENSITIVE),
        ("ssm", "get-parameter", RiskLevel.SENSITIVE),
        ("ec2", "describe-instances", RiskLevel.READ_ONLY),
    ],
)
def test_classifies_service_specific_risk(
    service_name: str, operation: str, expected: RiskLevel
) -> None:
    assert classify_operation(operation, service=service_name) is expected


def test_builds_universal_command_with_compact_json() -> None:
    service = UniversalAwsService(DemoAwsCliExecutor())
    context = AwsContext(profile="dev", region="sa-east-1")

    command = service.build_command(
        context,
        "ec2",
        "describe-instances",
        '{"InstanceIds": ["i-123"]}',
    )

    assert command.mutates is False
    assert command.arguments[:4] == (
        "ec2",
        "describe-instances",
        "--cli-input-json",
        '{"InstanceIds":["i-123"]}',
    )
    assert command.arguments[-7:] == (
        "--region",
        "sa-east-1",
        "--profile",
        "dev",
        "--output",
        "json",
        "--no-cli-pager",
    )


def test_rejects_context_override_in_extra_arguments() -> None:
    service = UniversalAwsService(DemoAwsCliExecutor())

    with pytest.raises(ValueError, match="controlada"):
        service.build_command(
            AwsContext(profile="dev", region="sa-east-1"),
            "s3api",
            "list-buckets",
            "{}",
            "--profile outra-conta",
        )


@pytest.mark.parametrize("option", ["--cli-input-json", "--debug", "--no-cli-pager"])
def test_rejects_security_control_override(option: str) -> None:
    service = UniversalAwsService(DemoAwsCliExecutor())

    with pytest.raises(ValueError, match="controlada"):
        service.build_command(
            AwsContext(profile="dev", region="sa-east-1"),
            "ec2",
            "describe-instances",
            "{}",
            option,
        )


def test_sensitive_read_does_not_claim_to_mutate_aws() -> None:
    command = UniversalAwsService(DemoAwsCliExecutor()).build_command(
        AwsContext(profile="dev", region="sa-east-1"),
        "secretsmanager",
        "get-secret-value",
        "{}",
    )

    assert command.mutates is False


def test_demo_generates_json_skeleton() -> None:
    service = UniversalAwsService(DemoAwsCliExecutor())

    skeleton = service.input_skeleton("ec2", "describe-instances")

    assert '"InstanceIds"' in skeleton
