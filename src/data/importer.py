"""Read-only XLSX ingestion. All sheets retained; normalized data is authoritative."""
import argparse
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from openpyxl import load_workbook
from src.config import Settings
from src.data.database import connect, initialize

def cents(v):
    return int((Decimal(str(v))*100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def read_source(path):
    book=load_workbook(path, read_only=True, data_only=True)
    result={}
    try:
        for s in book:
            it=iter(s.values); headers=next(it)
            if not all(isinstance(k,str) and k for k in headers) or len(set(headers))!=len(headers):
                raise ValueError(f'Invalid headers: {s.title}')
            result[s.title]=[dict(zip(headers,r)) for r in it if any(v is not None for v in r)]
    finally: book.close()
    return result

def import_data(settings=None):
    s=settings or Settings(); tables=read_source(s.source_path)
    fields={'categorias':{'category_id','name','description'},'clientes':{'customer_id','name','phone','email','city'},'produtos':{'product_id','category_id','name','description','price_brl','stock_quantity','status','specs_json','created_at'},'pedidos':{'order_id','customer_id','order_date','status','total_brl','payment_method','tracking_code','estimated_delivery','notes'},'itens_pedido':{'item_id','order_id','product_id','quantity'},'promocoes':{'promotion_id','product_id','discount_percent','description','is_active'}}
    for tab,keys in fields.items():
        if tab not in tables or not tables[tab] or not keys.issubset(tables[tab][0]): raise ValueError(f'Missing table/fields: {tab}')
    for tab,key in {'categorias':'category_id','clientes':'customer_id','produtos':'product_id','pedidos':'order_id','itens_pedido':'item_id','promocoes':'promotion_id'}.items():
        ids=[r[key] for r in tables[tab]]
        if any(isinstance(v,bool) or not isinstance(v,int) or v<=0 for v in ids) or len(set(ids))!=len(ids):
            raise ValueError(f'Invalid or duplicate identifiers: {tab}.{key}')
    initialize(s.database_path)
    with connect(s.database_path) as c:
        # UPSERT preserves session references and never resets historical chat/queue data.
        def insert(table,cols,records):
            values=list(records); colnames=cols.split(','); pk=colnames[0]
            sql=f'INSERT INTO {table}({cols}) VALUES ({",".join("?" for _ in colnames)}) ON CONFLICT({pk}) DO UPDATE SET '+','.join(f'{k}=excluded.{k}' for k in colnames[1:])
            c.executemany(sql,values)
        insert('categories','category_id,name,description',([r[k] for k in ['category_id','name','description']] for r in tables['categorias']))
        insert('customers','customer_id,name,phone,email,city,phone_e164',([r.get(k) for k in ['customer_id','name','phone','email','city','phone_e164']] for r in tables['clientes']))
        for r in tables['produtos']: json.loads(r['specs_json'])
        insert('products','product_id,category_id,name,description,price_cents,stock_quantity,status,specs_json,created_at,quality_status',([r['product_id'],r['category_id'],r['name'],r['description'],cents(r['price_brl']),r['stock_quantity'],r['status'],r['specs_json'],r['created_at'],r.get('quality_status','not_reviewed')] for r in tables['produtos']))
        insert('orders','order_id,customer_id,order_date,status,total_cents,payment_method,tracking_code,estimated_delivery,notes',([r['order_id'],r['customer_id'],r['order_date'],r['status'],cents(r['total_brl']),r['payment_method'],r['tracking_code'],r['estimated_delivery'],r['notes']] for r in tables['pedidos']))
        insert('order_items','item_id,order_id,product_id,quantity',([r[k] for k in ['item_id','order_id','product_id','quantity']] for r in tables['itens_pedido']))
        insert('promotions','promotion_id,product_id,discount_percent,description,is_active',([r[k] for k in ['promotion_id','product_id','discount_percent','description','is_active']] for r in tables['promocoes']))
        c.execute('DELETE FROM source_aux')
        c.executemany('INSERT INTO source_aux VALUES (?,?,?)',[(tab,i,json.dumps(r,ensure_ascii=False,default=str)) for tab,rows in tables.items() for i,r in enumerate(rows,2)])
        if c.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('Foreign key violation')
        c.execute('INSERT INTO import_runs(sha256) VALUES (?)',(hashlib.sha256(s.source_path.read_bytes()).hexdigest(),))
    return {k:len(v) for k,v in tables.items()}

if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(import_data(),indent=2,ensure_ascii=False))
