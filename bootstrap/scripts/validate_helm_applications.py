#!/usr/bin/env python3
"""Render every Argo CD Helm Application in a directory with its valuesObject."""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

import yaml


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
        print(f"rendered {path}: Application/{name}", file=sys.stderr)


def main() -> None:
    root = pathlib.Path(sys.argv[1])
    for path in sorted(root.glob("*.yaml")):
        render_application(path)


if __name__ == "__main__":
    main()
