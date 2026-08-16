# Publicação do Pablin CLI

## Preparar a versão

1. Atualize a versão em `pyproject.toml` e `src/easyaws/__init__.py`.
2. Registre as mudanças em `CHANGELOG.md`.
3. Execute os testes e gere os pacotes:

```powershell
pytest
python -m build
python -m twine check dist/*
```

## Testar no TestPyPI

Crie uma conta no TestPyPI e um token de API. Não salve o token no repositório.

```powershell
python -m twine upload --repository testpypi dist/*
python -m pip install --index-url https://test.pypi.org/simple/ `
  --extra-index-url https://pypi.org/simple pablin-cli
pablin --version
```

## Publicar no PyPI

O workflow `publish.yml` usa Trusted Publishing do PyPI, sem token permanente no
GitHub. Antes do primeiro release:

1. publique o repositório no GitHub;
2. crie o projeto `pablin-cli` no PyPI ou configure um publisher pendente;
3. no PyPI, associe o proprietário/repositório, workflow
   `.github/workflows/publish.yml` e ambiente `pypi`;
4. crie o ambiente `pypi` no GitHub e habilite aprovação manual, se desejado;
5. envie uma tag igual à versão, por exemplo `v0.1.0`.

```powershell
git tag v0.1.0
git push origin v0.1.0
```

Versões publicadas no PyPI não podem ser sobrescritas. Se algo estiver errado,
incremente a versão e publique uma nova distribuição.
