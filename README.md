# Pablin CLI

[![PyPI](https://img.shields.io/pypi/v/pablin-cli)](https://pypi.org/project/pablin-cli/)
[![CI](https://github.com/pablinrlq/pablin-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/pablinrlq/pablin-cli/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/pablin-cli)](https://pypi.org/project/pablin-cli/)

Uma interface visual, guiada e segura para a AWS CLI. O Pablin CLI ajuda você a
encontrar serviços e operações, preencher parâmetros e revisar o comando exato
antes de executá-lo.

> Projeto em estágio alpha. Sempre revise o comando, a conta e a região antes de
> confirmar uma operação mutável.

## O que já funciona

- mostra conta, principal, ARN, perfil e região assim que abre;
- troca de conta com confirmação, logout e limpeza restrita ao perfil atual;
- catálogo dinâmico baseado na versão local da AWS CLI;
- centenas de serviços e operações, sem uma lista fixa mantida pelo projeto;
- atalhos funcionais para EC2, S3, IAM, RDS, DynamoDB, CloudWatch, Logs, ECS,
  EKS, CloudFormation, SQS, SNS, Route 53 e Secrets Manager;
- formulário JSON gerado pelo `--generate-cli-skeleton input` oficial;
- argumentos extras e prévia do comando antes da execução;
- classificação em leitura, alteração e operação destrutiva;
- confirmação `CONFIRMAR` para alterações e `EXCLUIR` para exclusões;
- fluxo especializado para listar funções Lambda e alterar memória;
- modo de demonstração que não acessa a AWS.

O catálogo universal expõe o que a sua instalação da AWS CLI oferece. Algumas
operações complexas ainda exigem conhecimento dos parâmetros da AWS; elas não
possuem todas um formulário especializado como o fluxo de Lambda.

## Requisitos

- Python 3.11 ou mais recente;
- AWS CLI v2 instalada e disponível no `PATH`;
- credenciais AWS com apenas as permissões necessárias para cada operação.

## Instalação

A forma recomendada de instalar pelo PyPI é:

```powershell
pipx install pablin-cli
pablin
```

Com `pip`, também funciona:

```powershell
python -m pip install pablin-cli
pablin
```

O comando antigo `easyaws` continuará disponível por compatibilidade.

## Uso

Abra sem tocar numa conta real:

```powershell
pablin --demo
```

Confira se a AWS CLI foi encontrada:

```powershell
pablin --check
```

Use a conta AWS configurada:

```powershell
pablin
```

Também é possível executar como módulo:

```powershell
python -m pablin_cli --version
```

## Segurança

Os argumentos são enviados diretamente ao processo da AWS CLI, sem passar por
interpretação do PowerShell ou Bash. O Pablin CLI usa as credenciais e permissões
da AWS CLI e não armazena chaves próprias.

Na troca de conta, o programa pede confirmação, executa `aws logout`, remove
somente as chaves de autenticação do perfil escolhido e inicia `aws login`. Os
demais perfis não são modificados.

Operações classificadas como mutáveis ou destrutivas exigem confirmação humana.
Essa classificação é uma camada adicional de proteção, não uma substituição para
IAM com privilégio mínimo, ambientes de teste e revisão do comando.

## Desenvolvimento

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
pablin --demo
```

Para gerar e validar os arquivos de distribuição:

```powershell
python -m build
python -m twine check dist/*
```

Veja o [guia de publicação](https://github.com/pablinrlq/pablin-cli/blob/main/PUBLISHING.md)
para o processo de release.

## Licença e marcas

Distribuído sob a [licença MIT](https://github.com/pablinrlq/pablin-cli/blob/main/LICENSE).

Pablin CLI é um projeto independente e não é afiliado, patrocinado ou endossado
pela Amazon Web Services. AWS e Amazon Web Services são marcas de seus respectivos
proprietários.
