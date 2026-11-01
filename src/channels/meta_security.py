import hashlib
import hmac

def signature(secret,body):
    return 'sha256='+hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()

def valid_signature(secret,body,header):
    return bool(secret and header and hmac.compare_digest(signature(secret,body),header))
