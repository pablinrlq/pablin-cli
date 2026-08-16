# Contribuindo

Obrigado por contribuir com o Pablin CLI.

1. Crie um ambiente Python 3.11 ou mais recente.
2. Instale com `python -m pip install -e ".[dev]"`.
3. Faça mudanças pequenas e inclua testes.
4. Execute `pytest` antes de abrir o pull request.
5. Nunca inclua credenciais, arquivos `~/.aws`, tokens ou números de conta reais.

Mudanças que executem novas operações AWS devem mostrar o comando previamente,
classificar o risco e exigir confirmação quando houver mutação.
