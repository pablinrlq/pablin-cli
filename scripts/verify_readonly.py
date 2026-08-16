"""Validação de integração que não cria nem altera recursos AWS."""

from easyaws.aws_cli import AwsCliExecutor
from easyaws.catalog import AwsCliCatalog
from easyaws.models import AwsContext
from easyaws.universal_service import UniversalAwsService


def main() -> None:
    catalog = AwsCliCatalog()
    services = catalog.list_services()
    print(f"SERVICES={len(services)}")
    for service_name in ("ec2", "lambda", "s3api"):
        print(
            f"{service_name.upper()}_OPERATIONS="
            f"{len(catalog.list_operations(service_name))}"
        )
    print(
        "EC2_DESCRIBE_PARAMETERS="
        f"{len(catalog.list_parameters('ec2', 'describe-instances'))}"
    )

    universal = UniversalAwsService(AwsCliExecutor())
    command = universal.build_command(
        AwsContext(profile="default", region="sa-east-1"),
        "sts",
        "get-caller-identity",
        "{}",
    )
    print(universal.execute(command))


if __name__ == "__main__":
    main()
