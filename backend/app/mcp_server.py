"""Servidor MCP para cadastro e demonstrações CVM, usando a mesma base da API REST."""
from mcp.server.fastmcp import FastMCP
from .db import init_db, search_companies, get_company, financial_values

mcp = FastMCP('Atlas Fundamental', instructions='Consulte dados públicos da CVM. Informe sempre documento, período, demonstração e fonte. Não invente indicadores nem cotações.')

@mcp.tool()
def search_companies_tool(query: str, limit: int = 10) -> dict:
    """Pesquisa companhias no cadastro CVM sincronizado."""
    init_db()
    limit=max(1,min(int(limit),50))
    return {'query':query,'items':search_companies(query,limit),'source':'CVM cadastro de companhias abertas','note':'Cadastro societário não equivale a dados de cotação ou indicadores fundamentalistas.'}

@mcp.tool()
def company_by_cnpj(cnpj: str) -> dict:
    """Consulta uma companhia pelo CNPJ no cadastro CVM sincronizado."""
    init_db()
    item=get_company(cnpj)
    return item or {'error':'Companhia não encontrada','source':'CVM cadastro de companhias abertas'}

@mcp.tool()
def company_financial_statements(cnpj: str, year_from: int = 2020, statement: str = '', limit: int = 300) -> dict:
    """Consulta contas de DFP/ITR importadas da CVM. Demonstrações aceitas: DRE, BPA, BPP, DFC_MI, DFC_MD, DMPL, DRA."""
    init_db()
    item=get_company(cnpj)
    if not item:
        return {'error':'Companhia não encontrada no cadastro CVM','source':'CVM'}
    values=financial_values(cnpj, max(1990,int(year_from)), statement, max(1,min(int(limit),1000)))
    return {'company':item,'items':values,'total':len(values),'source':'CVM Dados Abertos DFP/ITR',
            'note':'Valores e unidade conforme arquivo original da CVM; não são cotações de mercado.'}

if __name__ == '__main__':
    init_db()
    mcp.run(transport='streamable-http')
