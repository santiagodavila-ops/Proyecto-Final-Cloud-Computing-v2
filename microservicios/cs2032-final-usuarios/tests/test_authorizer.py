import unittest
from unittest.mock import MagicMock, patch
import time

import authorizer


class TestAuthorizer(unittest.TestCase):

    def test_extraer_token_token_event(self):
        event = {
            "type": "TOKEN",
            "authorizationToken": "Bearer mi-token-secreto-123",
            "methodArn": "arn:aws:execute-api:us-east-1:123456789012:api123/dev/GET/usuarios/validar"
        }
        token = authorizer.extraer_token(event)
        self.assertEqual(token, "mi-token-secreto-123")

    def test_extraer_token_request_event(self):
        event = {
            "type": "REQUEST",
            "headers": {
                "Authorization": "Bearer token-request-456"
            },
            "methodArn": "arn:aws:execute-api:us-east-1:123456789012:api123/dev/GET/usuarios/validar"
        }
        token = authorizer.extraer_token(event)
        self.assertEqual(token, "token-request-456")

    def test_extraer_token_without_bearer_prefix(self):
        event = {
            "type": "TOKEN",
            "authorizationToken": "token-directo-789"
        }
        token = authorizer.extraer_token(event)
        self.assertEqual(token, "token-directo-789")

    def test_extraer_token_empty(self):
        self.assertIsNone(authorizer.extraer_token({}))
        self.assertIsNone(authorizer.extraer_token({"authorizationToken": ""}))

    def test_construir_recurso_wildcard(self):
        method_arn = "arn:aws:execute-api:us-east-1:816193343783:jas1g5t9tl/dev/GET/usuarios/validar"
        wildcard = authorizer.construir_recurso_wildcard(method_arn)
        self.assertEqual(wildcard, "arn:aws:execute-api:us-east-1:816193343783:*/*/*")

    def test_generar_politica(self):
        policy = authorizer.generar_politica(
            "user-123",
            "Allow",
            "arn:aws:execute-api:us-east-1:816193343783:*/*/*",
            context={"tenant_id": "tenant_1", "rol": "administrador"}
        )
        self.assertEqual(policy["principalId"], "user-123")
        self.assertEqual(policy["policyDocument"]["Statement"][0]["Effect"], "Allow")
        self.assertEqual(policy["policyDocument"]["Statement"][0]["Resource"], "arn:aws:execute-api:us-east-1:816193343783:*/*/*")
        self.assertEqual(policy["context"]["tenant_id"], "tenant_1")
        self.assertEqual(policy["context"]["rol"], "administrador")

    @patch("authorizer.tabla_tokens")
    @patch("authorizer.tabla_usuarios")
    def test_handler_allow(self, mock_tabla_usuarios, mock_tabla_tokens):
        ahora = int(time.time())
        mock_tabla_tokens.get_item.return_value = {
            "Item": {
                "token": "valid-token",
                "tipo": "acceso",
                "tenant_id": "tenant_1",
                "usuario_id": "usr-999",
                "rol": "administrador",
                "expira": ahora + 3600
            }
        }
        event = {
            "type": "TOKEN",
            "authorizationToken": "Bearer valid-token",
            "methodArn": "arn:aws:execute-api:us-east-1:816193343783:jas1g5t9tl/dev/GET/usuarios/validar"
        }
        res = authorizer.handler(event)
        self.assertEqual(res["principalId"], "usr-999")
        self.assertEqual(res["policyDocument"]["Statement"][0]["Effect"], "Allow")
        self.assertEqual(res["context"]["tenant_id"], "tenant_1")
        self.assertEqual(res["context"]["usuario_id"], "usr-999")
        self.assertEqual(res["context"]["rol"], "administrador")

    @patch("authorizer.tabla_tokens")
    def test_handler_deny_expired(self, mock_tabla_tokens):
        ahora = int(time.time())
        mock_tabla_tokens.get_item.return_value = {
            "Item": {
                "token": "expired-token",
                "tipo": "acceso",
                "tenant_id": "tenant_1",
                "usuario_id": "usr-999",
                "expira": ahora - 100
            }
        }
        event = {
            "type": "TOKEN",
            "authorizationToken": "Bearer expired-token",
            "methodArn": "arn:aws:execute-api:us-east-1:816193343783:jas1g5t9tl/dev/GET/usuarios/validar"
        }
        res = authorizer.handler(event)
        self.assertEqual(res["principalId"], "anonymous")
        self.assertEqual(res["policyDocument"]["Statement"][0]["Effect"], "Deny")

    @patch("authorizer.tabla_tokens")
    def test_handler_deny_refresh_type(self, mock_tabla_tokens):
        ahora = int(time.time())
        mock_tabla_tokens.get_item.return_value = {
            "Item": {
                "token": "refresh-token",
                "tipo": "refresh",
                "tenant_id": "tenant_1",
                "usuario_id": "usr-999",
                "expira": ahora + 3600
            }
        }
        event = {
            "type": "TOKEN",
            "authorizationToken": "Bearer refresh-token",
            "methodArn": "arn:aws:execute-api:us-east-1:816193343783:jas1g5t9tl/dev/GET/usuarios/validar"
        }
        res = authorizer.handler(event)
        self.assertEqual(res["principalId"], "anonymous")
        self.assertEqual(res["policyDocument"]["Statement"][0]["Effect"], "Deny")

    def test_handler_missing_token(self):
        event = {
            "type": "TOKEN",
            "authorizationToken": "",
            "methodArn": "arn:aws:execute-api:us-east-1:816193343783:jas1g5t9tl/dev/GET/usuarios/validar"
        }
        res = authorizer.handler(event)
        self.assertEqual(res["principalId"], "anonymous")
        self.assertEqual(res["policyDocument"]["Statement"][0]["Effect"], "Deny")

    def test_validar_token_from_request_context_authorizer(self):
        from common.auth import validar_token
        event = {
            "requestContext": {
                "authorizer": {
                    "tenant_id": "tenant_1",
                    "usuario_id": "usr-123",
                    "rol": "administrador"
                }
            }
        }
        item, error = validar_token(event)
        self.assertIsNone(error)
        self.assertEqual(item["tenant_id"], "tenant_1")
        self.assertEqual(item["usuario_id"], "usr-123")
        self.assertEqual(item["rol"], "administrador")


if __name__ == "__main__":
    unittest.main()
