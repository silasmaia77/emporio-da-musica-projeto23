from decimal import Decimal, ROUND_HALF_UP

def quote(price_cents, discount_percent=0, payment='credit', installments=1):
    if isinstance(price_cents,bool) or not isinstance(price_cents,int) or price_cents<0: raise ValueError('Invalid price')
    d=Decimal(str(discount_percent))
    if not 0<=d<=100 or payment not in {'pix','credit','debit','boleto'}: raise ValueError('Invalid payment/discount')
    if not isinstance(installments,int) or not 1<=installments<=12: raise ValueError('Invalid installments')
    if payment!='credit' and installments!=1: raise ValueError('Installments require credit')
    applied=d if d>0 else Decimal(5) if payment=='pix' else Decimal(0)
    total=int((Decimal(price_cents)*(1-applied/100)).quantize(Decimal(1),rounding=ROUND_HALF_UP))
    minimum=10000 if installments>=7 else 8000 if installments>=4 else 0
    # The under-R$50 wording is ambiguous: do not authorize multiple payments.
    if installments>1 and total<5000:return {'status':'needs_confirmation','reason':'Parcelamento abaixo de R$ 50 exige confirmação da equipe.'}
    if total//installments<minimum:return {'status':'not_allowed','reason':'Parcela abaixo do mínimo da faixa.'}
    base,remainder=divmod(total,installments)
    return {'status':'ok','original_cents':price_cents,'discount_percent':float(applied),'promotional':d>0,'total_cents':total,'payment':payment,'installments':installments,'installment_cents':[base+(i<remainder) for i in range(installments)],'interest_percent':0}

def local_shipping(total_cents):
    if total_cents==50000:return {'status':'needs_confirmation','reason':'Manual não define exatamente R$ 500,00.'}
    return {'status':'ok','shipping_cents':0 if total_cents>50000 else 3500,'business_days':[1,3]}
