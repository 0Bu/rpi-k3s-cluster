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
            subprocess.run(
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
                stdout=subprocess.DEVNULL,
            )
        print(f"rendered {path}: Application/{name}", file=sys.stderr)


def main() -> None:
    root = pathlib.Path(sys.argv[1])
    for path in sorted(root.glob("*.yaml")):
        render_application(path)


if __name__ == "__main__":
    main()
