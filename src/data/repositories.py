import json
from decimal import Decimal
from src.data.database import connect, normalize
from src.services.pricing import quote

def public_product(r):
    d=dict(r); specs=json.loads(d.pop('specs_json'))
    if d.get('quality_status')=='revisar':
        d['description']='Características técnicas precisam de confirmação pela equipe.'
        specs={}
    d['specs']=specs
    if d['active_promotion_count']>1:
        d['pricing_status']='needs_confirmation';d['discount_percent']=0
    else:d['pricing_status']='ok'
    d['credit_quote']=quote(d['price_cents'],d['discount_percent'])
    d['pix_quote']=quote(d['price_cents'],d['discount_percent'],'pix')
    return d

class StoreRepository:
    def __init__(self,path):self.path=path

    def search(self,query='',category='',max_price_brl=None,available_only=True,limit=5):
        limit=max(1,min(int(limit),10)); sql='SELECT * FROM catalog WHERE 1=1';args=[]
        # Split terms instead of requiring an exact contiguous phrase.
        aliases={'violao':'violoes','guitarra':'guitarras','baixo':'baixos','bateria':'baterias','teclado':'teclados','ukulele':'ukuleles'}
        for word in normalize(query).split():
            word=aliases.get(word,word)
            word=word.replace('%','\\%').replace('_','\\_')
            sql+=" AND norm(name || ' ' || category_name) LIKE ? ESCAPE '\\'";args.append('%'+word+'%')
        if category:sql+=' AND norm(category_name)=?';args.append(aliases.get(normalize(category),normalize(category)))
        if max_price_brl is not None:
            n=Decimal(str(max_price_brl))
            if not n.is_finite() or n<0:raise ValueError('Invalid budget')
            sql+=' AND price_cents <= ?';args.append(int(n*100))
        if available_only:sql+=' AND can_offer=1'
        sql+=' ORDER BY price_cents,product_id LIMIT ?';args.append(limit)
        with connect(self.path) as c:return [public_product(r) for r in c.execute(sql,args)]

    def product(self,product_id):
        with connect(self.path) as c:r=c.execute('SELECT * FROM catalog WHERE product_id=?',(product_id,)).fetchone()
        return public_product(r) if r else None

    def promotions(self,product_id=None):
        sql='SELECT promotion_id,product_id,discount_percent,description FROM promotions WHERE is_active=1';args=[]
        if product_id is not None:sql+=' AND product_id=?';args.append(product_id)
        with connect(self.path) as c:return [dict(r) for r in c.execute(sql+' LIMIT 30',args)]

    def order(self,order_id,customer_id):
        if customer_id is None:return {'status':'unauthorized','message':'É necessário verificar a identidade antes de consultar pedidos.'}
        with connect(self.path) as c:
            o=c.execute('SELECT order_id,order_date,status,total_cents,payment_method,tracking_code,estimated_delivery FROM orders WHERE order_id=? AND customer_id=?',(order_id,customer_id)).fetchone()
            if not o:return {'status':'not_found','message':'Pedido não encontrado para o cliente autorizado.'}
            items=[dict(r) for r in c.execute('SELECT i.product_id,p.name,i.quantity FROM order_items i JOIN products p USING(product_id) WHERE i.order_id=?',(order_id,))]
        return {'status':'ok','order':dict(o),'items':items,'actual_delivery_date':None,'purchase_channel':None}
