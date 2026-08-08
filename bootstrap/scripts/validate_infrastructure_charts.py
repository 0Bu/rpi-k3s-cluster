#!/usr/bin/env python3
"""Render pinned bootstrap infrastructure charts and verify key resources."""

from __future__ import annotations

import pathlib
import subprocess
import sys

import yaml


def main() -> None:
    values = yaml.safe_load(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    rendered = subprocess.run(
        [
            "helm",
            "template",
            "nfs-csi",
            "csi-driver-nfs",
            "--repo",
            values["nfs_csi_chart_repo"],
            "--version",
            str(values["nfs_csi_chart_version"]),
            "--namespace",
            "kube-system",
            "--set",
            "controller.replicas=1",
            "--set",
            "feature.enableFSGroupPolicy=true",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    resources = [resource for resource in yaml.safe_load_all(rendered.stdout) if resource]
    identities = {
        (resource["kind"], resource["metadata"]["name"])
        for resource in resources
    }
    required = {
        ("Deployment", "csi-nfs-controller"),
        ("DaemonSet", "csi-nfs-node"),
        ("CSIDriver", "nfs.csi.k8s.io"),
    }
    missing = required - identities
    if missing:
        raise SystemExit(f"NFS CSI chart is missing resources: {sorted(missing)}")
    print(
        f"rendered csi-driver-nfs {values['nfs_csi_chart_version']} "
        f"with {len(resources)} resources",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
