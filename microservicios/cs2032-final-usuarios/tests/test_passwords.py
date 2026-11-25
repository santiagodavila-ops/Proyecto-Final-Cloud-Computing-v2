import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.passwords import hashear_password, verificar_password


class TestPasswords(unittest.TestCase):
    def test_hash_nuevo_verifica(self):
        almacenado = hashear_password("secreto123")
        self.assertTrue(almacenado.startswith("pbkdf2_sha256$310000$"))
        self.assertEqual(verificar_password("secreto123", almacenado), (True, False))

    def test_hash_legado_verifica_y_pide_rehash(self):
        legado = hashlib.sha256("secreto123".encode("utf-8")).hexdigest()
        self.assertEqual(verificar_password("secreto123", legado), (True, True))

    def test_password_incorrecta_falla(self):
        nuevo = hashear_password("secreto123")
        legado = hashlib.sha256("secreto123".encode("utf-8")).hexdigest()
        self.assertEqual(verificar_password("otra", nuevo), (False, False))
        self.assertEqual(verificar_password("otra", legado), (False, False))

    def test_salt_distinta(self):
        self.assertNotEqual(hashear_password("igual"), hashear_password("igual"))


if __name__ == "__main__":
    unittest.main()
