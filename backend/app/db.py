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
        con.execute('''CREATE TABLE IF NOT EXISTS financial_values (
            cnpj TEXT NOT NULL, document TEXT NOT NULL, year INTEGER NOT NULL,
            reference_date TEXT NOT NULL DEFAULT '', exercise_order TEXT NOT NULL DEFAULT '',
            group_type TEXT NOT NULL DEFAULT '', statement TEXT NOT NULL,
            account_name TEXT NOT NULL DEFAULT '', account_code TEXT NOT NULL,
            value REAL NOT NULL, fixed_account TEXT NOT NULL DEFAULT '',
            source_file TEXT NOT NULL DEFAULT '', updated_at TEXT,
            UNIQUE(cnpj,document,year,reference_date,exercise_order,group_type,statement,account_code)
        )''')
        con.execute('CREATE INDEX IF NOT EXISTS idx_financial_cnpj_year ON financial_values(cnpj,year,document)')
        con.execute('CREATE INDEX IF NOT EXISTS idx_financial_account ON financial_values(statement,account_code)')

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

def financial_values(cnpj: str, year_from: int = 0, statement: str = '', limit: int = 500):
    digits = ''.join(ch for ch in cnpj if ch.isdigit())
    sql = '''SELECT cnpj,document,year,reference_date,exercise_order,group_type,statement,
                    account_name,account_code,value,fixed_account,source_file,updated_at
             FROM financial_values WHERE cnpj=?'''
    params = [digits]
    if year_from:
        sql += ' AND year>=?'; params.append(year_from)
    if statement:
        sql += ' AND statement=?'; params.append(statement.upper())
    sql += ' ORDER BY year DESC, statement, account_code LIMIT ?'; params.append(limit)
    with connect() as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]

def financial_count():
    with connect() as con:
        return con.execute('SELECT COUNT(*) FROM financial_values').fetchone()[0]

def set_metadata(key: str, value: str):
    with connect() as con:
        con.execute('INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key,value))

def get_metadata(key: str):
    with connect() as con:
        row=con.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
        return row['value'] if row else None
