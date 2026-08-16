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
