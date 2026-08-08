#!/usr/bin/env python3
"""Render every Argo CD Helm Application in a directory with its valuesObject."""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

import yaml


def require_secret_key_ref(values: dict, env_name: str, secret: str, key: str) -> None:
    actual = values.get("envValueFrom", {}).get(env_name, {}).get("secretKeyRef", {})
    expected = {"name": secret, "key": key}
    if actual != expected:
        raise RuntimeError(f"{env_name} must reference {secret}/{key}, got {actual}")


def validate_grafana_oauth(path: pathlib.Path, values: dict) -> None:
    oauth = values.get("grafana.ini", {}).get("auth.generic_oauth", {})
    if not oauth.get("enabled"):
        return
    require_secret_key_ref(
        values,
        "GF_AUTH_GENERIC_OAUTH_CLIENT_ID",
        "grafana-oauth",
        "client-id",
    )
    require_secret_key_ref(
        values,
        "GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET",
        "grafana-oauth",
        "client-secret",
    )
    if oauth.get("client_id") != "$__env{GF_AUTH_GENERIC_OAUTH_CLIENT_ID}":
        raise RuntimeError(f"{path}: Grafana OAuth client ID is not environment-backed")
    if oauth.get("client_secret") != "$__env{GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET}":
        raise RuntimeError(f"{path}: Grafana OAuth client secret is not environment-backed")
    if not oauth.get("role_attribute_strict"):
        raise RuntimeError(f"{path}: Grafana OAuth entitlement mapping is not strict")


def validate_authentik(path: pathlib.Path, values: dict, resources: list[dict]) -> None:
    if values.get("authentik", {}).get("existingSecret", {}).get("secretName") != "authentik-config":
        raise RuntimeError(f"{path}: Authentik configuration is not external-secret-backed")
    if values.get("postgresql", {}).get("auth", {}).get("existingSecret") != "authentik-postgresql":
        raise RuntimeError(f"{path}: PostgreSQL password is not external-secret-backed")

    forbidden = {"ClusterRole", "ClusterRoleBinding"}
    rendered_forbidden = sorted(
        resource["kind"] for resource in resources if resource.get("kind") in forbidden
    )
    if rendered_forbidden:
        raise RuntimeError(f"{path}: Authentik rendered cluster-wide RBAC {rendered_forbidden}")

    service_accounts = {
        resource["metadata"]["name"]: resource
        for resource in resources
        if resource.get("kind") == "ServiceAccount"
    }
    runtime_account = service_accounts.get("authentik-runtime")
    if not runtime_account or runtime_account.get("automountServiceAccountToken") is not False:
        raise RuntimeError(f"{path}: Authentik runtime ServiceAccount must disable token mounts")
    for deployment in (
        resource for resource in resources if resource.get("kind") == "Deployment"
    ):
        if deployment["metadata"]["name"] in {"authentik-server", "authentik-worker"}:
            account = deployment["spec"]["template"]["spec"].get("serviceAccountName")
            if account != "authentik-runtime":
                raise RuntimeError(
                    f"{path}: {deployment['metadata']['name']} uses ServiceAccount {account}"
                )

    claims = values.get("blueprints", {}).get("configMaps", [])
    if "authentik-blueprints" not in claims:
        raise RuntimeError(f"{path}: Authentik Grafana blueprint is not mounted")
    blueprint_objects = [
        resource
        for resource in resources
        if resource.get("kind") == "ConfigMap"
        and resource.get("metadata", {}).get("name") == "authentik-blueprints"
    ]
    if len(blueprint_objects) != 1:
        raise RuntimeError(f"{path}: expected one Authentik blueprint ConfigMap")
    blueprint = blueprint_objects[0].get("data", {}).get("grafana.yaml", "")
    for marker in (
        "!Env HOMELAB_GRAFANA_CLIENT_SECRET",
        "!Env HOMELAB_OLEG_PASSWORD",
        "authentik_core.applicationentitlement",
    ):
        if marker not in blueprint:
            raise RuntimeError(f"{path}: Authentik blueprint is missing {marker}")


def render_application(path: pathlib.Path) -> None:
    for document in yaml.safe_load_all(path.read_text(encoding="utf-8")):
        if not document or document.get("kind") != "Application":
            continue

        source = document["spec"]["source"]
        if "chart" not in source:
            continue

        name = document["metadata"]["name"]
        namespace = document["spec"]["destination"]["namespace"]
        values = source.get("helm", {}).get("valuesObject", {})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as values_file:
            yaml.safe_dump(values, values_file, sort_keys=False)
            values_file.flush()
            rendered = subprocess.run(
                [
                    "helm",
                    "template",
                    name,
                    source["chart"],
                    "--repo",
                    source["repoURL"],
                    "--version",
                    str(source["targetRevision"]),
                    "--namespace",
                    namespace,
                    "--values",
                    values_file.name,
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        resources = [
            resource
            for resource in yaml.safe_load_all(rendered.stdout)
            if resource
        ]
        expected_service = values.get("service", {})
        if expected_service.get("ipFamilyPolicy"):
            services = [resource for resource in resources if resource.get("kind") == "Service"]
            if not services:
                raise RuntimeError(f"{path}: rendered chart has no Service")
            for service in services:
                spec = service["spec"]
                if spec.get("ipFamilyPolicy") != expected_service["ipFamilyPolicy"]:
                    raise RuntimeError(f"{path}: Service lost ipFamilyPolicy")
                if spec.get("ipFamilies") != expected_service.get("ipFamilies"):
                    raise RuntimeError(f"{path}: Service lost requested ipFamilies")

        expected_hosts = values.get("ingress", {}).get("hosts", [])
        if not expected_hosts:
            expected_hosts = values.get("server", {}).get("ingress", {}).get("hosts", [])
        if expected_hosts:
            ingresses = [resource for resource in resources if resource.get("kind") == "Ingress"]
            rendered_hosts = {
                rule["host"]
                for ingress in ingresses
                for rule in ingress["spec"].get("rules", [])
            }
            if rendered_hosts != set(expected_hosts):
                raise RuntimeError(
                    f"{path}: rendered Ingress hosts {rendered_hosts} != {set(expected_hosts)}"
                )

        if name == "grafana":
            validate_grafana_oauth(path, values)
        if name == "authentik":
            validate_authentik(path, values, resources)
        print(f"rendered {path}: Application/{name}", file=sys.stderr)


def main() -> None:
    root = pathlib.Path(sys.argv[1])
    for path in sorted(root.glob("*.yaml")):
        render_application(path)


if __name__ == "__main__":
    main()
