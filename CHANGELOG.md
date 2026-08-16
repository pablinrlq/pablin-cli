# Changelog

Todas as mudanças relevantes do Pablin CLI serão registradas aqui.

## 0.3.0 - 2026-08-16

- endpoints customizados ignorados por padrão para evitar redirecionamento de
  chamadas AWS assinadas;
- limite de 8 MiB para saída de subprocessos, sem retenção integral em memória;
- confirmação para leituras sensíveis e comandos que podem gravar arquivos;
- troca de conta limpa todas as fontes de autenticação conflitantes e verifica se
  a AWS CLI resolveu credenciais do tipo `login`;
- argumentos capazes de substituir controles internos agora são bloqueados;
- dependências fixadas e auditorias Bandit/pip-audit adicionadas ao CI e release;
- GitHub Actions fixadas em commits verificados e Dependabot configurado;
- projeto promovido de alpha para beta.

## 0.2.0 - 2026-08-16

- atalhos funcionais para EC2, S3, IAM, RDS, DynamoDB, CloudWatch, Logs, ECS,
  EKS, CloudFormation, SQS, SNS, Route 53 e Secrets Manager;
- abertura direta do serviço escolhido no explorador universal;
- menu lateral rolável para comportar mais serviços;
- remoção de todos os botões marcados como “em breve”.

## 0.1.0 - 2026-08-15

- primeira versão pública;
- identificação e troca segura de conta AWS;
- catálogo dinâmico de serviços, operações e parâmetros da AWS CLI;
- prévia, classificação de risco e confirmação de comandos;
- fluxo guiado para AWS Lambda;
- modo de demonstração sem acesso à AWS.
