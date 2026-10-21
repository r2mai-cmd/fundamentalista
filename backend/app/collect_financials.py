"""Importa demonstrações anuais DFP/ITR da CVM para uma tabela padronizada.
Fontes oficiais: arquivos ZIP públicos da CVM. Os valores permanecem na unidade divulgada
pela CVM (geralmente milhares de reais); a API retorna também conta, exercício e documento.
"""
import csv, io, os, zipfile
from datetime import datetime, timezone
import httpx
from .db import init_db, connect, set_metadata

BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"
DOCS = ("DFP", "ITR")
YEARS_BACK = int(os.getenv("CVM_FINANCIAL_YEARS", "5"))
# Arquivos mais úteis para a primeira camada; consolidado e individual são identificados.
STATEMENTS = ("DRE", "BPA", "BPP", "DFC_MI", "DFC_MD", "DMPL", "DRA")

def norm(row):
    return {str(k).strip().upper(): (v or "").strip() for k, v in row.items()}

def first(row, *keys):
    for key in keys:
        value = row.get(key, "")
        if value:
            return value
    return ""

def parse_number(value):
    if not value:
        return None
    value = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None

def run():
    init_db()
    current_year = datetime.now(timezone.utc).year
    years = range(current_year - YEARS_BACK + 1, current_year + 1)
    loaded = 0
    failures = []
    with httpx.Client(timeout=120, follow_redirects=True, headers={"User-Agent":"AtlasFundamental/0.2 public-data"}) as client:
        for doc in DOCS:
            for year in years:
                url = f"{BASE}/{doc}/DADOS/{doc.lower()}_cia_aberta_{year}.zip"
                try:
                    response = client.get(url)
                    if response.status_code == 404:
                        continue
                    response.raise_for_status()
                    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                        names = archive.namelist()
                        for statement in STATEMENTS:
                            # CVM filenames vary in case; select consolidated and individual files.
                            candidates = [n for n in names if n.lower().endswith(".csv")
                                          and f"_{statement.lower()}_" in n.lower()
                                          and f"_{year}" in n.lower()]
                            for name in candidates:
                                raw = archive.read(name)
                                try:
                                    content = raw.decode("utf-8-sig")
                                except UnicodeDecodeError:
                                    content = raw.decode("latin-1")
                                reader = csv.DictReader(io.StringIO(content), delimiter=";")
                                rows = []
                                for raw_row in reader:
                                    row = norm(raw_row)
                                    cnpj = "".join(ch for ch in first(row, "CNPJ_CIA", "CNPJ") if ch.isdigit())
                                    account = first(row, "CD_CONTA", "CD_CONTA_REF")
                                    value = parse_number(first(row, "VL_CONTA"))
                                    if not cnpj or not account or value is None:
                                        continue
                                    rows.append((
                                        cnpj, doc, year, first(row, "DT_REFER"),
                                        first(row, "ORDEM_EXERC"), first(row, "GRUPO_DFP"),
                                        statement, first(row, "DS_CONTA"), account, value,
                                        first(row, "ST_CONTA_FIXA"), name,
                                        datetime.now(timezone.utc).isoformat()
                                    ))
                                if rows:
                                    with connect() as con:
                                        con.executemany("""INSERT INTO financial_values
                                          (cnpj,document,year,reference_date,exercise_order,group_type,statement,
                                           account_name,account_code,value,fixed_account,source_file,updated_at)
                                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                                          ON CONFLICT(cnpj,document,year,reference_date,exercise_order,group_type,statement,account_code)
                                          DO UPDATE SET account_name=excluded.account_name,value=excluded.value,
                                          source_file=excluded.source_file,updated_at=excluded.updated_at""", rows)
                                    loaded += len(rows)
                except Exception as exc:
                    failures.append(f"{doc}/{year}: {type(exc).__name__}: {exc}")
    set_metadata("financials_last_sync", datetime.now(timezone.utc).isoformat())
    set_metadata("financials_rows_loaded", str(loaded))
    if failures:
        print("Algumas fontes não foram importadas:")
        for failure in failures[:20]:
            print(" -", failure)
    print(f"Importação DFP/ITR concluída: {loaded} valores contábeis processados.")
    if loaded == 0:
        raise RuntimeError("Nenhum dado DFP/ITR foi importado. Verifique URLs e formato dos arquivos da CVM.")

if __name__ == "__main__":
    run()
