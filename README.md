# Atlas Fundamental — MVP 0.3

Plataforma independente para explorar dados públicos de companhias brasileiras, com dashboard web, REST API e servidor MCP.

## Dados disponíveis no código

- Cadastro público de companhias abertas da CVM.
- Importador DFP/ITR: DRE, BPA, BPP, DFC-MI, DFC-MD, DMPL e DRA.
- API REST para pesquisa de companhias e consulta às demonstrações importadas.
- MCP para pesquisar empresas, consultar CNPJ e obter contas de demonstrações.
- Workflow de sincronização que pode ser acionado manualmente ou a cada seis horas.
- Dashboard com temas claro e escuro.

## Fontes oficiais

- Cadastro CVM: https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/
- DFP: https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/
- ITR: https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/

Os arquivos DFP/ITR são CSVs dentro de ZIPs anuais. Os dados importados preservam código e descrição da conta, exercício, documento, tipo de demonstração e arquivo de origem. Confira unidade, grupo consolidado/individual, período e reapresentações. Este MVP ainda não calcula múltiplos como P/L, ROE ou EV/EBITDA e não contém cotações de mercado.

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

Documentação: http://127.0.0.1:8000/docs

### Endpoints

- `GET /api/health` — estado geral e contagens.
- `GET /api/financials/health` — estado dos dados contábeis.
- `GET /api/companies?q=Petrobras` — pesquisa de empresas.
- `GET /api/companies/{cnpj}/financials?year_from=2020&statement=DRE` — demonstrações.
- `POST /api/admin/sync` — inicia sincronização protegida.
- `GET /api/admin/sync/status` — consulta o estado da sincronização protegida.

O endpoint administrativo exige o cabeçalho `X-Atlas-Sync-Token`, comparado à variável de ambiente `ATLAS_SYNC_TOKEN`. Nunca publique esse token no frontend.

MCP: `python -m app.mcp_server`. A ferramenta `company_financial_statements` consulta a mesma camada de dados.

## Ativar a sincronização automática em produção

O workflow `.github/workflows/sync-cvm.yml` tenta acionar a API a cada seis horas e também pode ser executado manualmente. Para ativá-lo:

1. Implante a versão atualizada do backend em um serviço com armazenamento persistente.
2. Configure no serviço a variável secreta `ATLAS_SYNC_TOKEN` com um token forte e aleatório.
3. No GitHub, abra **Settings → Secrets and variables → Actions → New repository secret**.
4. Crie `ATLAS_API_URL` com a URL base pública da API (sem barra final) e `ATLAS_SYNC_TOKEN` com o mesmo token configurado no backend.
5. Abra **Actions → Sync public CVM data → Run workflow** para testar a primeira execução.
6. Consulte `/api/admin/sync/status` usando o mesmo cabeçalho de autenticação. Verifique também `/api/health` e `/api/financials/health`.

A agenda do GitHub Actions é best-effort e pode atrasar. A sincronização roda em segundo plano no backend; se o provedor reiniciar o serviço durante a importação, a tarefa pode ser interrompida. Para maior confiabilidade e grande volume, migre para PostgreSQL e um worker/cron separado com monitoramento, retries e alertas.

## Publicação

O frontend é publicado pelo GitHub Pages via `.github/workflows/pages.yml`. O backend precisa de um serviço Python/container e armazenamento persistente. Se estiver usando SQLite, API e MCP precisam compartilhar o mesmo arquivo de banco em um ambiente compatível; não use SQLite separado para cada serviço.

## Transparência e limites

O código da sincronização está preparado, mas só haverá atualização automática depois que o backend for implantado com a variável `ATLAS_SYNC_TOKEN` e os dois GitHub Actions secrets forem configurados. A importação real precisa ser validada após a primeira execução. Os dados da CVM podem conter reapresentações. Cotações, preços históricos, proventos e dados de mercado da B3 ainda não estão integrados; futuras integrações devem respeitar disponibilidade, condições de uso e licenças.
