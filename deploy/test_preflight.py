"""Run with: python -m unittest discover -s deploy -p 'test_*.py'."""
import copy
import json
import unittest
from preflight import validate


class ProductionChecks(unittest.TestCase):
    def setUp(self):
        env = {"EMAIL_OTP_ENABLED": "true", "AUTH_ALLOW_LOCAL_HTTP": "false",
            "ENVIRONMENT": "production", "RUN_STARTUP_MIGRATIONS": "false", "CREATE_STORAGE_BUCKET": "false",
            "AUTH_LOCAL_ORIGIN": "", "HF_HOME": "/home/researchiq/.cache/huggingface",
            "AUTH_ORIGIN": "https://research.university.edu", "MYSQL_USER": "researchiq",
            "MYSQL_PASSWORD": "a" * 32, "SECRET_KEY": "b" * 32,
            "AUTH_OTP_SECRET": "c" * 32, "MINIO_SECRET_KEY": "d" * 32,
            "SMTP_HOST": "smtp.university.edu", "SMTP_USERNAME": "mailer", "SMTP_PASSWORD": "test-only",
            "SMTP_FROM_EMAIL": "research@university.edu", "SMTP_SECURITY": "starttls",
            "MINIO_ACCESS_KEY": "storage-user", "OPENAI_API_KEY": "test-only-key",
            "AUTH_TRUSTED_PROXIES": json.dumps(["172.30.240.10/32"])}
        self.config = {"services": {"backend": {"environment": env, "image": "backend:verified",
            "command": ["uvicorn", "--no-proxy-headers"], "user": "10001:10001", "read_only": True,
            "cap_drop": ["ALL"], "security_opt": ["no-new-privileges:true"],
            "tmpfs": ["/tmp:rw,noexec,nosuid,nodev,size=256m,mode=1777"],
            "networks": {"app_network": {}, "data_network": {}},
            "volumes": [{"type": "volume", "target": "/app/uploads"},
                        {"type": "volume", "target": "/home/researchiq/.cache/huggingface"}]},
            "frontend": {"image": "frontend:verified", "networks": {"app_network": {}}},
            "db": {"environment": {"MYSQL_ROOT_PASSWORD": "e" * 32}, "networks": {"data_network": {}}},
            "minio": {"environment": {"MINIO_ROOT_USER": "bootstrap", "MINIO_ROOT_PASSWORD": "f" * 32},
                      "networks": {"data_network": {}}},
            "chromadb": {"networks": {"data_network": {}}},
            "nginx": {"environment": {"PUBLIC_DOMAIN": "research.university.edu"},
            "ports": [{"published": "80"}, {"published": "443"}],
            "networks": {"app_network": {"ipv4_address": "172.30.240.10"}}}},
            "volumes": {"data": {"external": True}},
            "networks": {"data_network": {"internal": True}}}

    def test_valid_configuration(self):
        self.assertEqual(validate(self.config), [])
        self.config["services"]["backend"]["environment"]["SMTP_SECURITY"] = "ssl"
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

    def test_workstream_one_boundaries(self):
        mutations = [
            lambda c: c["services"]["backend"]["environment"].update(ENVIRONMENT="development"),
            lambda c: c["services"]["backend"]["environment"].update(AUTH_LOCAL_ORIGIN="http://127.0.0.1.nip.io"),
            lambda c: c["services"]["backend"]["environment"].update(RUN_STARTUP_MIGRATIONS="true"),
            lambda c: c["services"]["backend"]["environment"].update(CREATE_STORAGE_BUCKET="true"),
            lambda c: c["services"]["backend"]["environment"].update(MYSQL_ROOT_PASSWORD="do-not-echo"),
            lambda c: c["services"]["backend"]["environment"].update(SQLALCHEMY_DATABASE_URI="do-not-echo"),
            lambda c: c["services"]["backend"].update(env_file=["shared.env"]),
            lambda c: c["services"]["backend"].update(user="0:0"),
            lambda c: c["services"]["backend"].update(read_only=False),
            lambda c: c["services"]["backend"].update(cap_add=["SYS_ADMIN"]),
            lambda c: c["services"]["backend"].update(cap_drop=[]),
            lambda c: c["services"]["backend"].update(security_opt=[]),
            lambda c: c["services"]["backend"].update(tmpfs=[]),
            lambda c: c["services"]["backend"]["volumes"].append({"type": "volume", "target": "/app"}),
            lambda c: c["services"]["frontend"]["networks"].update(data_network={}),
            lambda c: c["services"]["nginx"]["networks"].update(data_network={}),
            lambda c: c["services"]["chromadb"].update(ports=[{"published": "8001"}]),
            lambda c: c["services"]["minio"].update(ports=[{"published": "9000"}]),
            lambda c: c["services"].pop("chromadb"),
            lambda c: c["services"]["minio"]["environment"].update(MINIO_ROOT_USER="storage-user"),
            lambda c: c["services"]["minio"]["environment"].update(MINIO_ROOT_PASSWORD="d" * 32),
            lambda c: c["services"]["db"]["environment"].update(MYSQL_USER="runtime"),
        ]
        for change in mutations:
            with self.subTest(change=change):
                config = copy.deepcopy(self.config)
                change(config)
                errors = validate(config)
                self.assertTrue(errors)
                self.assertNotIn("do-not-echo", " ".join(errors))
