import os, sqlite3
from pathlib import Path

DB_PATH = os.getenv('ATLAS_DB_PATH', str(Path(__file__).resolve().parents[1] / 'atlas.db'))

def connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS companies (
            cnpj TEXT PRIMARY KEY, name TEXT NOT NULL, trade_name TEXT,
            status TEXT, source TEXT NOT NULL DEFAULT 'CVM', updated_at TEXT
        )''')
        con.execute('''CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        )''')

def company_count():
    with connect() as con:
        return con.execute('SELECT COUNT(*) FROM companies').fetchone()[0]

def search_companies(q: str, limit: int = 50):
    with connect() as con:
        rows = con.execute('''SELECT cnpj, name, trade_name, status, source, updated_at
          FROM companies WHERE name LIKE ? OR trade_name LIKE ? OR cnpj LIKE ?
          ORDER BY name LIMIT ?''', (f'%{q}%', f'%{q}%', f'%{q}%', limit)).fetchall()
        return [dict(r) for r in rows]

def get_company(cnpj: str):
    digits = ''.join(ch for ch in cnpj if ch.isdigit())
    with connect() as con:
        row = con.execute('SELECT cnpj, name, trade_name, status, source, updated_at FROM companies WHERE cnpj=?', (digits,)).fetchone()
        return dict(row) if row else None

def set_metadata(key: str, value: str):
    with connect() as con:
        con.execute('INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key,value))

def get_metadata(key: str):
    with connect() as con:
        row=con.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
        return row['value'] if row else None
