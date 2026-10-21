"""Servidor MCP separado; usa a mesma camada de dados do REST API.
Execute: python -m app.mcp_server (porta 8001 por padrão).
"""
from mcp.server.fastmcp import FastMCP
from .db import init_db, search_companies, get_company

mcp = FastMCP('Atlas Fundamental', instructions='Consulte cadastro público de companhias brasileiras sincronizado a partir da CVM. Não invente indicadores nem cotações.')

@mcp.tool()
def search_companies_tool(query: str, limit: int = 10) -> dict:
    """Pesquisa companhias no cadastro CVM sincronizado. Retorna nomes, CNPJs e situação cadastral."""
    init_db()
    limit=max(1,min(int(limit),50))
    return {'query':query,'items':search_companies(query,limit),'source':'CVM cadastro de companhias abertas','note':'Cadastro societário não equivale a dados de cotação ou indicadores fundamentalistas.'}

@mcp.tool()
def company_by_cnpj(cnpj: str) -> dict:
    """Consulta uma companhia pelo CNPJ no cadastro CVM sincronizado."""
    init_db()
    item=get_company(cnpj)
    return item or {'error':'Companhia não encontrada','source':'CVM cadastro de companhias abertas'}

if __name__ == '__main__':
    init_db()
    mcp.run(transport='streamable-http')
