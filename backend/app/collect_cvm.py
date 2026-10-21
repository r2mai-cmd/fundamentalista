"""Sincroniza cadastro público de companhias abertas da CVM para SQLite.
Não coleta cotações nem indicadores calculados. Confira o leia-me e termos da fonte antes de produção.
"""
import csv, io, os
from datetime import datetime, timezone
import httpx
from .db import init_db, connect, set_metadata

URL = os.getenv('CVM_COMPANY_CSV_URL','https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv')

def pick(row, *candidates):
    normalized={str(k).strip().upper(): (v or '').strip() for k,v in row.items()}
    for key in candidates:
        if normalized.get(key): return normalized[key]
    return ''

def run():
    init_db()
    with httpx.Client(timeout=90, follow_redirects=True, headers={'User-Agent':'AtlasFundamental/0.1 (public data research)'}) as client:
        response=client.get(URL); response.raise_for_status()
    # CVM datasets commonly use Latin-1; fall back only when needed.
    try: content=response.content.decode('utf-8-sig')
    except UnicodeDecodeError: content=response.content.decode('latin-1')
    reader=csv.DictReader(io.StringIO(content), delimiter=';')
    rows=[]
    for row in reader:
        cnpj=pick(row,'CNPJ_CIA','CNPJ')
        name=pick(row,'DENOM_SOCIAL','DENOMINACAO_SOCIAL','NOME_EMPRESARIAL')
        if not cnpj or not name: continue
        cnpj=''.join(ch for ch in cnpj if ch.isdigit())
        rows.append((cnpj,name,pick(row,'DENOM_COMERC','NOME_COMERCIAL'),pick(row,'SIT','SITUACAO'), 'CVM', datetime.now(timezone.utc).isoformat()))
    if not rows: raise RuntimeError('O arquivo foi baixado, mas nenhum registro reconhecido. Confira o formato atualizado do CSV da CVM.')
    with connect() as con:
        con.executemany('''INSERT INTO companies(cnpj,name,trade_name,status,source,updated_at) VALUES(?,?,?,?,?,?)
          ON CONFLICT(cnpj) DO UPDATE SET name=excluded.name,trade_name=excluded.trade_name,status=excluded.status,source=excluded.source,updated_at=excluded.updated_at''', rows)
    set_metadata('last_sync',datetime.now(timezone.utc).isoformat())
    print(f'Sincronização concluída: {len(rows)} registros lidos da CVM.')

if __name__=='__main__': run()
