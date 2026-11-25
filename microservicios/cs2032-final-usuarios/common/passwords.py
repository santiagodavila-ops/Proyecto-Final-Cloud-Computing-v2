import hashlib
import hmac
import secrets

PREFIJO = "pbkdf2_sha256"
ITERACIONES = 310000
LONGITUD_SALT = 16


def _derivar(password, salt, iteraciones):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iteraciones)


def hashear_password(password):
    # Formato: pbkdf2_sha256$<iteraciones>$<salt_hex>$<hash_hex>
    salt = secrets.token_bytes(LONGITUD_SALT)
    derivado = _derivar(password, salt, ITERACIONES)
    return f"{PREFIJO}${ITERACIONES}${salt.hex()}${derivado.hex()}"


def verificar_password(password, almacenado):
    # Devuelve (ok, necesita_rehash); los hashes legados sha256 piden rehash
    if not isinstance(almacenado, str) or not isinstance(password, str):
        return False, False
    if almacenado.startswith(PREFIJO + "$"):
        try:
            _, iteraciones, salt_hex, hash_hex = almacenado.split("$")
            derivado = _derivar(password, bytes.fromhex(salt_hex), int(iteraciones))
        except ValueError:
            return False, False
        return hmac.compare_digest(derivado.hex(), hash_hex), False
    # Hash legado: sha256 hexadecimal sin sal
    legado = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if hmac.compare_digest(legado, almacenado):
        return True, True
    return False, False
