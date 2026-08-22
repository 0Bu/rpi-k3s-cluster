#!/usr/bin/env python3
"""Validate that real Argo CD desired state cannot come from the public repo."""

from __future__ import annotations

import pathlib
import re
import sys

import yaml


PUBLIC_REPOSITORY = "0Bu/rpi-k3s-cluster"
SSH_REPOSITORY = re.compile(r"^git@github\.com:([^/]+/[^/]+)\.git$")


def fail(message: str) -> None:
    raise SystemExit(f"GitOps boundary validation failed: {message}")


def main() -> None:
    common_path = pathlib.Path(sys.argv[1]).resolve()
    common = yaml.safe_load(common_path.read_text(encoding="utf-8"))
    cluster = yaml.safe_load(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))

    repo_url = str(common.get("gitops_repo_url", ""))
    match = SSH_REPOSITORY.fullmatch(repo_url)
    if match is None:
        fail("gitops_repo_url must be a GitHub SSH URL for deploy-key isolation")
    if match.group(1) == PUBLIC_REPOSITORY:
        fail("real Applications must not be sourced from the public infrastructure repository")
    if match.group(1) != common.get("gitops_repo_github_slug"):
        fail("gitops_repo_url and gitops_repo_github_slug disagree")
    if common.get("gitops_target_revision") != "main":
        fail("the private desired-state repository must use its protected main branch")
    if not str(common.get("gitops_repo_deploy_key_title", "")).endswith("-read-only"):
        fail("the deploy-key title must make its read-only contract explicit")
    if cluster.get("gitops_path") != f"clusters/{cluster['cluster_name']}/argocd":
        fail("each cluster root must be confined to its own private overlay")

    public_cluster_dir = common_path.parents[2] / "clusters"
    leaked_overlays = sorted(
        path.relative_to(common_path.parents[2])
        for path in public_cluster_dir.rglob("*")
        if path.is_file() and path.name != "README.md"
    )
    if leaked_overlays:
        fail(
            "real cluster files returned to the public repository: "
            + ", ".join(map(str, leaked_overlays))
        )

    print(
        f"validated private GitOps repo={match.group(1)} "
        f"revision=main path={cluster['gitops_path']}"
    )


if __name__ == "__main__":
    main()
