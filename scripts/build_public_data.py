#!/usr/bin/env python3
"""Build a small static public-company directory from the official CVM CSV."""
import csv, json, os, urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
OUT = Path("frontend/data/companies.json")
req = urllib.request.Request(URL, headers={"User-Agent": "AtlasFundamental/0.3 public-data"})
with urllib.request.urlopen(req, timeout=90) as response:
    raw = response.read()
try:
    text = raw.decode("utf-8-sig")
except UnicodeDecodeError:
    text = raw.decode("latin-1")
reader = csv.DictReader(text.splitlines(), delimiter=";")
items = []
for row in reader:
    row = {(k or "").strip().upper(): (v or "").strip() for k, v in row.items()}
    cnpj = "".join(ch for ch in (row.get("CNPJ_CIA") or row.get("CNPJ") or "") if ch.isdigit())
    name = row.get("DENOM_SOCIAL") or row.get("DENOMINACAO_SOCIAL") or row.get("NOME_EMPRESARIAL") or ""
    if not cnpj or not name:
        continue
    items.append({
        "cnpj": cnpj,
        "name": name,
        "trade_name": row.get("DENOM_COMERC", ""),
        "status": row.get("SIT", ""),
        "source": "CVM",
    })
if not items:
    raise SystemExit("CVM CSV downloaded but no recognized company records; refusing to overwrite data.")
OUT.parent.mkdir(parents=True, exist_ok=True)
payload = {"source": "CVM Dados Abertos", "source_url": URL,
           "updated_at": datetime.now(timezone.utc).isoformat(),
           "count": len(items), "items": items}
OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
print(f"Wrote {len(items)} company records to {OUT}")
