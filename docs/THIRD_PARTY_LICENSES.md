# Licenças de Terceiros (Third-Party Licenses)

O **Study Reviewer** é distribuído sob a licença MIT ([LICENSE](../LICENSE)) e incorpora ou adapta os seguintes componentes de terceiros em seus assets locais:

---

## 1. HTMX (`1.9.12`)

* **Arquivo local:** `src/adapters/web/static/js/htmx.min.js`
* **Projeto:** HTMX (Carson Gross / Big Sky Software)
* **Licença:** BSD 2-Clause ("Simplified" BSD License)
* **Resumo dos termos:** Permite redistribuição e uso em formato fonte ou binário, com ou sem modificações, desde que preservados o aviso de copyright, a lista de condições e a isenção de responsabilidade aplicável à licença BSD-2-Clause.

---

## 2. Game-Icons.net (Ícones Vetoriais RPG)

* **Arquivos locais:** `src/adapters/web/rpg_icons.py` e `src/adapters/web/static/js/rpg_icons.js`
* **Origem:** Caminhos vetoriais SVG (`512x512`) adaptados da coleção Game-Icons.net
* **Licença:** Creative Commons Attribution 3.0 Unported (CC BY 3.0)
* **Resumo dos termos:** Uso, adaptação e redistribuição permitidos mediante atribuição apropriada ao projeto Game-Icons.net e indicação de adaptações realizadas.

---

## 3. Dependências Python e Ferramentas de Build

As dependências declaradas em `pyproject.toml` (como FastAPI, Uvicorn, SQLAlchemy, Pydantic, Jinja2, Cryptography, Alembic, nh3, pypdf, python-docx e httpx) e ferramentas de frontend (`package.json` / Tailwind CSS) permanecem sujeitas às respectivas licenças open-source de seus mantenedores (MIT, BSD, Apache-2.0 e PSF).
