from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .db import init_db, company_count, search_companies, get_company, get_metadata

app = FastAPI(title='Atlas Fundamental API', version='0.1.0', description='API independente para dados públicos de companhias brasileiras.')
origins = [x.strip() for x in __import__('os').getenv('CORS_ORIGINS','*').split(',') if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=['GET','OPTIONS'], allow_headers=['*'])

@app.on_event('startup')
def startup(): init_db()

@app.get('/')
def root(): return {'name':'Atlas Fundamental API','version':'0.1.0','docs':'/docs','health':'/api/health'}

@app.get('/api/health')
def health():
    return {'status':'ok','company_count':company_count(),'last_sync':get_metadata('last_sync'),'timestamp':datetime.now(timezone.utc).isoformat(),'data_status':'public_registry_only' if company_count() else 'empty'}

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
