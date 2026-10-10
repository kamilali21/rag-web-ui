"""Read-only production checks. Never print resolved environment values/secrets."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def validate(config):
    errors = []
    services = config["services"]
    backend = services["backend"]
    env = backend["environment"]
    edge = services["nginx"]
    domain = edge["environment"]["PUBLIC_DOMAIN"]
    if (not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}", domain)
            or "example." in domain or domain.endswith((".localhost", ".test", ".invalid", ".nip.io"))):
        errors.append("Set a real public DNS hostname (no scheme, port or path).")
    if (str(env.get("EMAIL_OTP_ENABLED")).lower() != "true"
            or str(env.get("AUTH_ALLOW_LOCAL_HTTP")).lower() != "false"
            or env.get("AUTH_ORIGIN") != "https://" + domain):
        errors.append("Production requires email verification and an exact HTTPS origin.")
    secret_names = ["MYSQL_PASSWORD", "SECRET_KEY", "AUTH_OTP_SECRET", "MINIO_SECRET_KEY"]
    secrets = [env.get(name, "") for name in secret_names]
    secrets.append(services["db"]["environment"].get("MYSQL_ROOT_PASSWORD", ""))
    if (any(len(value) < 32 or "CHANGE_ME" in value or "your-" in value for value in secrets)
            or len(set(secrets)) != len(secrets)):
        errors.append("Use independent random database/root/storage/JWT/OTP secrets of at least 32 characters.")
    if env.get("MYSQL_USER") == "root":
        errors.append("The application must use a non-root database account.")
    for name in ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL", "MINIO_ACCESS_KEY"]:
        if not env.get(name) or "CHANGE_ME" in env[name]:
            errors.append("Configure " + name + ".")
    if env.get("SMTP_SECURITY") not in {"starttls", "tls"}:
        errors.append("SMTP must use TLS or STARTTLS.")
    # Existing chat requires the configured provider key; never silently use a placeholder.
    provider = env.get("CHAT_PROVIDER", "openai").lower()
    provider_keys = {"openai": "OPENAI_API_KEY", "deepseek": "DEEPSEEK_API_KEY", "minimax": "MINIMAX_API_KEY"}
    if provider in provider_keys:
        value = env.get(provider_keys[provider], "")
        if not value or "CHANGE_ME" in value or value.startswith("your-"):
            errors.append("Configure the selected model provider's API key.")
    try:
        proxy = edge["networks"]["app_network"]["ipv4_address"]
        ipaddress.ip_address(proxy)
        assert json.loads(env["AUTH_TRUSTED_PROXIES"]) == [proxy + "/32"]
        assert "--no-proxy-headers" in backend["command"]
    except (KeyError, ValueError, AssertionError):
        errors.append("Trust only the configured nginx peer; disable uvicorn proxy-header rewriting.")
    for name, service in services.items():
        if service.get("privileged") or service.get("network_mode") == "host":
            errors.append(name + " must not use privileged/host-network mode.")
        if name != "nginx" and service.get("ports"):
            errors.append(name + " must not publish host ports.")
        if name in {"backend", "frontend"}:
            if any(v.get("type") == "bind" for v in service.get("volumes", [])):
                errors.append(name + " must not bind-mount application source.")
            image = service.get("image", "")
            if (not image or "CHANGE_ME" in image or image.endswith(":latest")
                    or ":" not in image.rsplit("/", 1)[-1]):
                errors.append(name + " requires a tested explicit image tag or digest.")
    for name in ["db", "chromadb", "minio"]:
        if name in services and set(services[name].get("networks", {})) != {"data_network"}:
            errors.append(name + " must use only the isolated data network.")
    if not config.get("networks", {}).get("data_network", {}).get("internal"):
        errors.append("The data network must be internal.")
    if {str(p["published"]) for p in edge.get("ports", [])} != {"80", "443"}:
        errors.append("Only HTTP redirect and HTTPS ports should be published.")
    if any(not volume.get("external") for volume in config["volumes"].values()):
        errors.append("Production data/cache volumes must be explicitly prepared external volumes.")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env.production")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    env_file = Path(args.env_file).resolve()
    if not env_file.is_file():
        parser.error("Create a private production environment file from deploy/production.env.example.")
    result = subprocess.run(["docker", "compose", "--env-file", str(env_file), "-f",
        str(root / "docker-compose.production.yml"), "config", "--format", "json"],
        env={**os.environ, "RESEARCHIQ_PRODUCTION_ENV": str(env_file)}, capture_output=True, text=True)
    if result.returncode:
        print("FAIL: Compose configuration is incomplete; check required settings locally.")
        return 1
    config = json.loads(result.stdout)
    errors = validate(config)
    for volume in config["volumes"].values():
        found = subprocess.run(["docker", "volume", "inspect", volume["name"]], capture_output=True)
        if found.returncode:
            errors.append("A declared external volume is missing; prepare/restore it before deployment.")
    mounts = config["services"]["nginx"]["volumes"]
    tls = next((Path(v["source"]) for v in mounts if v["target"] == "/etc/nginx/tls"), None)
    if tls is None or not all((tls / name).is_file() for name in ["fullchain.pem", "privkey.pem"]):
        errors.append("Install the domain certificate/full chain and private key in TLS_DIRECTORY.")
    for error in errors:
        print("FAIL:", error)
    if not errors:
        print("Configuration checks passed. DNS, certificate validity, SMTP delivery, image advisories and live acceptance still require verification.")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
