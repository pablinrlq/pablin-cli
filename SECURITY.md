# Segurança

## Relatando uma vulnerabilidade

Não publique credenciais, tokens, números de conta ou detalhes exploráveis em uma
issue pública. Quando o repositório estiver no GitHub, use um Security Advisory
privado do repositório para relatar vulnerabilidades.

Revogue imediatamente qualquer credencial AWS que tenha sido exposta e revise o
CloudTrail da conta afetada.

## Escopo

O Pablin CLI executa a AWS CLI local com as permissões da identidade selecionada.
Confirmações na interface reduzem erros acidentais, mas não substituem políticas
IAM de privilégio mínimo, MFA, SCPs ou processos de aprovação da organização.

## Proteções padrão

- execução da AWS CLI com argumentos separados e sem shell;
- conta, perfil, região e comando completos exibidos antes da confirmação;
- endpoints customizados ignorados, salvo liberação explícita com
  `PABLIN_ALLOW_CUSTOM_ENDPOINTS=1`;
- limite de 8 MiB para a saída capturada de cada comando;
- confirmação adicional para respostas sensíveis e operações que gravam arquivos;
- publicação no PyPI por OIDC, sem token permanente;
- dependências e GitHub Actions fixados em versões/commits revisados.

O suporte a endpoints customizados existe para ambientes locais confiáveis. Não
ative essa opção ao usar credenciais reais com um endpoint de terceiros.

## Versões suportadas

Apenas a versão mais recente publicada no PyPI recebe correções de segurança.
