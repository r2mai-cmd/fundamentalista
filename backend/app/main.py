from datetime import datetime, timezone
import os
from threading import Lock, Thread
from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from .db import init_db, company_count, search_companies, get_company, get_metadata, financial_values, financial_count

app = FastAPI(title='Atlas Fundamental API', version='0.3.0', description='API independente para dados públicos de companhias brasileiras.')
origins = [x.strip() for x in os.getenv('CORS_ORIGINS','*').split(',') if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=['GET','POST','OPTIONS'], allow_headers=['*'])
_sync_lock = Lock()
_sync_state = {'running': False, 'started_at': None, 'finished_at': None, 'error': None}

@app.on_event('startup')
def startup(): init_db()

@app.get('/')
def root(): return {'name':'Atlas Fundamental API','version':'0.3.0','docs':'/docs','health':'/api/health'}

@app.get('/api/health')
def health():
    return {'status':'ok','company_count':company_count(),'financial_value_count':financial_count(),
            'last_sync':get_metadata('last_sync'),'financials_last_sync':get_metadata('financials_last_sync'),
            'timestamp':datetime.now(timezone.utc).isoformat(),
            'data_status':'financials_and_registry' if financial_count() else ('public_registry_only' if company_count() else 'empty')}

@app.get('/api/companies')
def companies(q: str = Query(default='', max_length=120), limit: int = Query(default=50, ge=1, le=200)):
    if not q.strip(): return {'items':[], 'total':0, 'message':'Informe q para pesquisar o cadastro de companhias.'}
    items=search_companies(q.strip(),limit)
    return {'items':items,'total':len(items),'query':q,'source':'CVM cadastro de companhias abertas'}

@app.get('/api/companies/{cnpj}')
def company(cnpj: str):
    item=get_company(cnpj)
    if not item: raise HTTPException(status_code=404, detail='Companhia não encontrada no cadastro sincronizado.')
    return item

@app.get('/api/companies/{cnpj}/financials')
def company_financials(cnpj: str, year_from: int = Query(default=2020, ge=1990, le=2100),
                       statement: str = Query(default='', pattern='^(|DRE|BPA|BPP|DFC_MI|DFC_MD|DMPL|DRA)$'),
                       limit: int = Query(default=500, ge=1, le=5000)):
    item=get_company(cnpj)
    if not item: raise HTTPException(status_code=404, detail='Companhia não encontrada no cadastro sincronizado.')
    values=financial_values(cnpj,year_from,statement,limit)
    return {'company':item,'items':values,'total':len(values),'source':'CVM Dados Abertos DFP/ITR',
            'units_note':'Unidade e escala conforme arquivo original da CVM; confira a documentação da fonte.',
            'last_sync':get_metadata('financials_last_sync')}

@app.get('/api/financials/health')
def financials_health():
    return {'rows':financial_count(),'last_sync':get_metadata('financials_last_sync'),
            'source':'CVM Dados Abertos DFP/ITR','available_statements':['DRE','BPA','BPP','DFC_MI','DFC_MD','DMPL','DRA']}

def _run_sync():
    try:
        from .collect_cvm import run as run_cvm
        from .collect_financials import run as run_financials
        run_cvm()
        run_financials()
        _sync_state['error'] = None
    except Exception as exc:
        _sync_state['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        _sync_state['finished_at'] = datetime.now(timezone.utc).isoformat()
        _sync_state['running'] = False
        _sync_lock.release()

@app.post('/api/admin/sync')
def start_sync(x_atlas_sync_token: str = Header(default='')):
    expected = os.getenv('ATLAS_SYNC_TOKEN', '')
    if not expected or x_atlas_sync_token != expected:
        raise HTTPException(status_code=403, detail='Token de sincronização inválido ou não configurado.')
    if not _sync_lock.acquire(blocking=False):
        return {'status':'already_running', **_sync_state}
    _sync_state.update({'running': True, 'started_at': datetime.now(timezone.utc).isoformat(),
                        'finished_at': None, 'error': None})
    Thread(target=_run_sync, daemon=True).start()
    return {'status':'started', 'started_at':_sync_state['started_at'],
            'message':'Sincronização iniciada em segundo plano. Consulte /api/admin/sync/status.'}

@app.get('/api/admin/sync/status')
def sync_status(x_atlas_sync_token: str = Header(default='')):
    expected = os.getenv('ATLAS_SYNC_TOKEN', '')
    if not expected or x_atlas_sync_token != expected:
        raise HTTPException(status_code=403, detail='Token de sincronização inválido ou não configurado.')
    return dict(_sync_state)
