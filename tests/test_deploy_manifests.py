"""Static validation of the container image and K3s deployment resources."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "deploy" / "k8s" / "base"
OVERLAY = ROOT / "deploy" / "k8s" / "overlays" / "prod"


def _documents() -> list[dict]:
    documents: list[dict] = []
    for path in sorted(BASE.glob("*.yaml")):
        if path.name == "kustomization.yaml":
            continue
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            documents.append(loaded)
    return documents


def _by_kind(kind: str) -> dict:
    matches = [document for document in _documents() if document.get("kind") == kind]
    assert matches, f"missing {kind}"
    return matches[0]


def test_base_contains_required_resources():
    kinds = {document.get("kind") for document in _documents()}
    assert kinds >= {
        "Namespace",
        "ConfigMap",
        "Secret",
        "PersistentVolumeClaim",
        "Deployment",
        "Service",
        "Ingress",
        "CronJob",
        "NetworkPolicy",
    }
    pvcs = [
        document
        for document in _documents()
        if document.get("kind") == "PersistentVolumeClaim"
    ]
    assert len(pvcs) == 2
    assert {pvc["metadata"]["name"] for pvc in pvcs} == {
        "situlearn-data",
        "situlearn-backup",
    }


def test_deployment_has_probes_resources_and_storage():
    deployment = _by_kind("Deployment")
    spec = deployment["spec"]
    assert spec["replicas"] == 1
    assert spec["strategy"]["type"] == "Recreate"

    container = spec["template"]["spec"]["containers"][0]
    assert container["ports"][0]["containerPort"] == 8000
    assert container["livenessProbe"]["httpGet"]["path"] == "/healthz"
    assert container["readinessProbe"]["httpGet"]["path"] == "/readyz"
    assert container["resources"]["requests"]["cpu"] == "100m"
    assert container["resources"]["limits"]["memory"] == "512Mi"
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    mounts = {mount["mountPath"] for mount in container["volumeMounts"]}
    assert {"/data", "/backup", "/tmp"}.issubset(mounts)

    volumes = {
        volume["name"]: volume for volume in spec["template"]["spec"]["volumes"]
    }
    assert volumes["data"]["persistentVolumeClaim"]["claimName"] == "situlearn-data"
    assert volumes["backup"]["persistentVolumeClaim"]["claimName"] == "situlearn-backup"


def test_service_ingress_and_tls():
    service = _by_kind("Service")
    assert service["spec"]["ports"][0]["targetPort"] == "http"

    ingress = _by_kind("Ingress")
    assert ingress["spec"]["ingressClassName"] == "traefik"
    assert ingress["spec"]["tls"][0]["secretName"] == "situlearn-tls"
    assert ingress["spec"]["rules"][0]["host"] == "situlearn.example.com"


def test_configmap_and_secret_contract():
    config = _by_kind("ConfigMap")["data"]
    assert config["SITE_BASE_URL"].startswith("https://")
    assert config["MAX_REPORT_BYTES"] == "104857600"
    assert config["PREVIOUS_VERSION_TTL_H"] == "24"
    assert config["LOG_LEVEL"] == "info"

    secret = _by_kind("Secret")
    assert "PUBLISH_TOKEN" in secret["stringData"]
    assert "replace-with" in secret["stringData"]["PUBLISH_TOKEN"]


def test_backup_cronjob_mounts_both_volumes():
    cronjob = _by_kind("CronJob")
    assert cronjob["spec"]["schedule"] == "17 3 * * *"
    assert cronjob["spec"]["concurrencyPolicy"] == "Forbid"
    container = cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"][
        "containers"
    ][0]
    script = container["args"][0]
    assert "tar -czf /backup/" in script
    assert "-mtime +7 -delete" in script


def test_network_policy_scopes_traffic():
    policy = _by_kind("NetworkPolicy")
    assert set(policy["spec"]["policyTypes"]) == {"Ingress", "Egress"}
    assert policy["spec"]["ingress"][0]["ports"][0]["port"] == 8000
    assert policy["spec"]["egress"][0]["ports"][0]["port"] == 53


def test_dockerfile_runs_as_non_root_and_uses_locked_dependencies():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "uv sync --frozen --no-dev" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert '"situlearn.web.app:app"' in dockerfile
    assert "SITULEARN_DATA_DIR=/data" in dockerfile
    assert "SITULEARN_BACKUP_DIR=/backup" in dockerfile


def test_overlay_pins_image_tag_and_host():
    overlay = yaml.safe_load(
        (OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")
    )
    assert overlay["images"][0]["newTag"] == "0.2.0"
    assert overlay["namespace"] == "situlearn"
    patch_text = "\n".join(item["patch"] for item in overlay["patches"])
    assert "situlearn.example.com" in patch_text
    assert "SITE_BASE_URL" in patch_text


def test_kustomize_builds_when_kubectl_is_available():
    kubectl = shutil.which("kubectl")
    if not kubectl:
        pytest.skip("kubectl is not installed")
    result = subprocess.run(
        [kubectl, "kustomize", str(OVERLAY)],
        capture_output=True,
        check=True,
        text=True,
    )
    kinds = {document.get("kind") for document in yaml.safe_load_all(result.stdout)}
    assert "Deployment" in kinds
    assert "Ingress" in kinds
    assert "CronJob" in kinds
