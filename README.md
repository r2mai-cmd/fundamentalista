# Atlas Fundamental — MVP 0.2

Plataforma independente para explorar dados públicos de companhias brasileiras, com dashboard web estático, REST API e servidor MCP.

## Dados disponíveis no código

- Cadastro público de companhias abertas da CVM.
- Importador de demonstrações DFP/ITR: DRE, BPA, BPP, DFC-MI, DFC-MD, DMPL e DRA.
- API REST para pesquisa de companhias e consulta às demonstrações importadas.
- Ferramenta MCP para pesquisar empresas, consultar CNPJ e obter contas de demonstrações.
- Dashboard com temas claro e escuro e pesquisa de empresas.

## Fontes oficiais

- Cadastro CVM: https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/
- DFP: https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/
- ITR: https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/

Os arquivos DFP/ITR são CSVs dentro de ZIPs anuais. Os dados importados preservam código e descrição da conta, exercício, documento, tipo de demonstração e arquivo de origem. Antes de usar em análise, confira unidade, grupo consolidado/individual, período e reapresentações. O MVP ainda não calcula múltiplos como P/L, ROE ou EV/EBITDA e não contém cotações de mercado.

## Rodar localmente

Requer Python 3.11+.

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Em outro terminal, importar cadastro e demonstrações:

```bash
cd backend
python -m app.collect_cvm
python -m app.collect_financials
```

Documentação interativa: http://127.0.0.1:8000/docs

### Endpoints novos

- `GET /api/financials/health`
- `GET /api/companies/{cnpj}/financials?year_from=2020&statement=DRE`

O endpoint de demonstrações aceita `DRE`, `BPA`, `BPP`, `DFC_MI`, `DFC_MD`, `DMPL` ou `DRA`. Sem `statement`, retorna os tipos disponíveis para a empresa, sujeito ao limite de registros.

MCP: `python -m app.mcp_server`. A ferramenta `company_financial_statements` consulta a mesma base usada pela API.

## Publicação

O frontend é publicado pelo GitHub Pages usando `.github/workflows/pages.yml`. O backend precisa de um serviço Python/container e banco persistente. O importador DFP/ITR está implementado, mas precisa ser executado no ambiente que tenha acesso ao banco de produção para que a API passe a retornar esses registros. Não há importação automática no serviço de produção ainda.

Para produção, recomenda-se PostgreSQL compartilhado entre API e MCP, tarefas agendadas de ingestão, autenticação, rate limiting, logs, testes e backups. Configure CORS para a origem exata do GitHub Pages.

## Transparência

Os dados são da CVM e podem conter reapresentações. Cada resposta informa a fonte e preserva o nome do arquivo. Os dados de mercado da B3, preços históricos e proventos não estão integrados nesta versão. Integrações futuras devem respeitar disponibilidade, condições de uso e licenças aplicáveis.
