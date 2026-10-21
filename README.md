# Atlas Fundamental — MVP 0.1

Plataforma independente para explorar dados públicos de companhias brasileiras, com dashboard web estático, REST API e servidor MCP usando a mesma camada de dados.

## O que está pronto nesta entrega

- Dashboard responsivo em HTML/CSS/JS, com busca e estado de conexão da API.
- REST API FastAPI: `GET /api/health`, `GET /api/companies?q=...`, `GET /api/companies/{cnpj}`.
- Coletor inicial do cadastro de companhias abertas da CVM para SQLite.
- Servidor MCP com ferramentas `search_companies_tool` e `company_by_cnpj`.
- Workflow de GitHub Pages para publicar o frontend.
- Configuração de deploy do backend via Render Blueprint/Docker.
- Protótipo anterior preservado em `frontend/prototipo-landing.html`.

## Limites importantes

Este MVP ainda não implementa demonstrações financeiras DFP/ITR, indicadores calculados, preços históricos, proventos, fundos ou dados de mercado da B3. O coletor só tenta importar o cadastro CVM e pode precisar de ajuste caso a CVM altere os nomes/formatos das colunas. Não há dados de cotação simulados apresentados como reais. Integração com B3 deve respeitar disponibilidade, condições de uso e licenças aplicáveis.

## Rodar localmente

Requer Python 3.11+.

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Em outro terminal, sincronize o cadastro público:

```bash
cd backend
python -m app.collect_cvm
```

API: `http://127.0.0.1:8000/docs`.

Servidor MCP separado, em outro terminal:

```bash
cd backend
python -m app.mcp_server
```

O MCP usa transporte Streamable HTTP; confira a URL exata exibida pela versão do SDK instalada. Por padrão, o SDK FastMCP costuma expor o endpoint em `/mcp`.

## Conectar o dashboard ao backend

Edite `frontend/config.js`:

```js
window.ATLAS_CONFIG = { API_BASE_URL: "https://SUA-API-PUBLICA" };
```

Para desenvolvimento local, use `http://127.0.0.1:8000`. A URL do backend deve ser HTTPS quando o frontend estiver publicado em HTTPS. Configure `CORS_ORIGINS` no backend com a origem exata do GitHub Pages (por exemplo, `https://usuario.github.io`).

## Publicar frontend no GitHub Pages

1. Crie um repositório GitHub chamado `atlas-fundamental`.
2. Envie o conteúdo desta pasta para a raiz do repositório, mantendo `.github/workflows/`.
3. Em **Settings → Pages**, selecione **GitHub Actions** como origem.
4. A workflow `Deploy Atlas Fundamental frontend` publica a pasta `frontend/`.
5. Configure `frontend/config.js` com a URL do backend e faça novo commit.

## Publicar backend

O GitHub Pages só hospeda arquivos estáticos. O backend precisa de um serviço que execute containers ou Python. Este repositório inclui `render.yaml` e `backend/Dockerfile` como ponto de partida. Revise o valor `CORS_ORIGINS` e configure disco persistente. Para produção com mais tráfego, migre SQLite para PostgreSQL e implemente autenticação, rate limiting, observabilidade, testes e backups.

**Nota sobre MCP:** para produção, o REST API e o MCP devem compartilhar o mesmo serviço de domínio de dados, mas o processo MCP pode ser implantado como serviço separado. O código atual usa a mesma camada de persistência SQLite local; em produção, configure o mesmo banco persistente ou PostgreSQL compartilhado para ambos os serviços.

## Fontes e transparência

- CVM Dados Abertos: https://dados.cvm.gov.br/
- B3: https://www.b3.com.br/

Registrar a fonte, a data de extração e a data de referência de cada dado financeiro é requisito do produto, não um detalhe de apresentação.


## Identidade visual

A interface usa um sistema visual editorial próprio: fundo marfim, verde-floresta, azul cobalto e terracota, navegação superior horizontal, tipografia Manrope/DM Sans e cartões claros com bordas discretas. A proposta é diferenciar o Atlas de referências de mercado com um visual de pesquisa financeira contemporâneo, em vez de replicar um terminal escuro.
