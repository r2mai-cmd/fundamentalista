#!/usr/bin/env python3
"""Build Atlas public-company directory by combining CVM open companies and B3 tradable instruments."""
import csv, io, json, re, unicodedata, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path

CVM_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
B3_URL = "https://bvmf.bmfbovespa.com.br/suplemento/ExecutaAcaoDownload.asp?arquivo=Titulos_Negociaveis.zip&server=L"
OUT = Path("frontend/data/companies.json")
HEADERS = {"User-Agent": "Mozilla/5.0 AtlasFundamental/0.4 (+public-data)"}

def download(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()

def norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().upper()
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    # Normalize common legal suffixes to improve CVM/B3 name matching.
    value = re.sub(r"\b(S A|SA|S A A|SAA|CIA|COMPANHIA|EMPRESA|BRASIL|DO|DA|DE|DAS|DOS)\b", " ", value)
    return " ".join(value.split())

def load_cvm():
    raw = download(CVM_URL)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    companies = {}
    for original in csv.DictReader(io.StringIO(text), delimiter=";"):
        row = {(k or "").strip().upper(): (v or "").strip() for k, v in original.items()}
        cnpj = "".join(ch for ch in (row.get("CNPJ_CIA") or row.get("CNPJ") or "") if ch.isdigit())
        name = row.get("DENOM_SOCIAL") or row.get("DENOMINACAO_SOCIAL") or row.get("NOME_EMPRESARIAL") or ""
        status = row.get("SIT", "").upper()
        if not cnpj or not name or ("ATIVO" not in status and "EM FUNCIONAMENTO" not in status):
            continue
        companies[cnpj] = {"cnpj": cnpj, "name": name, "trade_name": row.get("DENOM_COMERC", ""),
                           "status": status or "ATIVO", "source": "CVM / B3", "tickers": []}
    return companies

def load_b3_instruments():
    raw = download(B3_URL)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        candidates = [n for n in archive.namelist() if n.lower().endswith((".txt", ".dat", ".csv"))]
        if not candidates:
            raise RuntimeError("ZIP B3 sem arquivo TXT/CSV reconhecível")
        data = archive.read(candidates[0])
    text = data.decode("latin-1", errors="replace")
    company_names, instruments = {}, []
    for line in text.splitlines():
        if len(line) < 18:
            continue
        kind = line[0:2]
        if kind == "01":
            code, name = line[2:6].strip(), line[6:66].strip()
            if code and name:
                company_names[code] = name
        elif kind == "02":
            ticker, company_code = line[2:14].strip(), line[14:18].strip()
            market = line[108:111].strip()
            market_desc = line[111:126].strip().upper()
            bdi = line[18:21].strip()
            # Keep spot-market instruments; derivatives/options/futures are not company stock tickers.
            if ticker and company_code and ("VISTA" in market_desc or market in {"010", "020"}):
                instruments.append({"ticker": ticker, "b3_code": company_code,
                                    "b3_name": company_names.get(company_code, ""),
                                    "market": market_desc, "bdi": bdi})
    if not instruments:
        raise RuntimeError("Arquivo B3 baixado, mas nenhum instrumento de mercado à vista foi reconhecido")
    return instruments

def main():
    companies = load_cvm()
    instruments = load_b3_instruments()
    by_name = {}
    for cnpj, company in companies.items():
        for name in (company["name"], company.get("trade_name", "")):
            key = norm(name)
            if key:
                by_name.setdefault(key, []).append(cnpj)
    # Match B3 issuer names to active CVM company records. Do not silently publish an unfiltered CVM directory.
    matched = {}
    unmatched = 0
    for instrument in instruments:
        b3_name = instrument["b3_name"]
        key = norm(b3_name)
        candidates = by_name.get(key, [])
        if not candidates:
            # Exact normalized prefix match handles occasional suffix differences without broad fuzzy matching.
            candidates = [cnpj for n, ids in by_name.items()
                          if len(key) >= 10 and len(n) >= 10 and (key.startswith(n) or n.startswith(key))
                          for cnpj in ids]
        if not candidates:
            unmatched += 1
            continue
        cnpj = candidates[0]
        company = matched.setdefault(cnpj, dict(companies[cnpj]))
        if instrument["ticker"] not in company["tickers"]:
            company["tickers"].append(instrument["ticker"])
    items = sorted(matched.values(), key=lambda c: c["name"].casefold())
    if not items:
        raise RuntimeError("Nenhuma empresa CVM foi associada aos instrumentos B3; dados anteriores preservados")
    for item in items:
        item["tickers"].sort()
        item["ticker"] = item["tickers"][0] if item["tickers"] else ""
    payload = {
        "source": "CVM Dados Abertos + B3 Títulos Negociáveis",
        "source_urls": [CVM_URL, B3_URL],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "ticker_count": sum(len(c["tickers"]) for c in items),
        "unmatched_b3_instruments": unmatched,
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {len(items)} matched CVM companies and {payload['ticker_count']} B3 tickers to {OUT}; unmatched B3 instruments: {unmatched}")

if __name__ == "__main__":
    main()
