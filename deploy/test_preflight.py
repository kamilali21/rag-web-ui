"""Run with: python -m unittest discover -s deploy -p 'test_*.py'."""
import copy
import json
import unittest
from preflight import validate


class ProductionChecks(unittest.TestCase):
    def setUp(self):
        env = {"EMAIL_OTP_ENABLED": "true", "AUTH_ALLOW_LOCAL_HTTP": "false",
            "AUTH_ORIGIN": "https://research.university.edu", "MYSQL_USER": "researchiq",
            "MYSQL_PASSWORD": "a" * 32, "SECRET_KEY": "b" * 32,
            "AUTH_OTP_SECRET": "c" * 32, "MINIO_SECRET_KEY": "d" * 32,
            "SMTP_HOST": "smtp.university.edu", "SMTP_USERNAME": "mailer", "SMTP_PASSWORD": "test-only",
            "SMTP_FROM_EMAIL": "research@university.edu", "SMTP_SECURITY": "starttls",
            "MINIO_ACCESS_KEY": "storage-user", "OPENAI_API_KEY": "test-only-key",
            "AUTH_TRUSTED_PROXIES": json.dumps(["172.30.240.10/32"])}
        self.config = {"services": {"backend": {"environment": env, "image": "backend:verified",
            "command": ["uvicorn", "--no-proxy-headers"]}, "frontend": {"image": "frontend:verified"},
            "db": {"environment": {"MYSQL_ROOT_PASSWORD": "e" * 32}, "networks": {"data_network": {}}},
            "nginx": {"environment": {"PUBLIC_DOMAIN": "research.university.edu"},
            "ports": [{"published": "80"}, {"published": "443"}],
            "networks": {"app_network": {"ipv4_address": "172.30.240.10"}}}},
            "volumes": {"data": {"external": True}},
            "networks": {"data_network": {"internal": True}}}

    def test_valid_configuration(self):
        self.assertEqual(validate(self.config), [])

    def test_rejects_public_stores_source_mounts_and_local_auth(self):
        changes = [lambda c: c["services"]["db"].update(ports=[{"published": "3306"}]),
            lambda c: c["services"]["backend"].update(volumes=[{"type": "bind"}]),
            lambda c: c["services"]["backend"]["environment"].update(AUTH_ALLOW_LOCAL_HTTP="true"),
            lambda c: c["services"]["backend"]["environment"].update(AUTH_TRUSTED_PROXIES='["0.0.0.0/0"]'),
            lambda c: c["services"]["backend"]["environment"].update(MYSQL_PASSWORD="CHANGE_ME"),
            lambda c: c["services"]["nginx"]["environment"].update(PUBLIC_DOMAIN="host; injected"),
            lambda c: c["volumes"]["data"].update(external=False),
            lambda c: c["services"]["frontend"].update(image="registry:5000/frontend"),
            lambda c: c["networks"]["data_network"].update(internal=False)]
        for change in changes:
            with self.subTest(change=change):
                config = copy.deepcopy(self.config)
                change(config)
                self.assertTrue(validate(config))
