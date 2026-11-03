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
    assert len(pvcs) == 1
    assert {pvc["metadata"]["name"] for pvc in pvcs} == {"situlearn-data"}


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
    assert {"/data", "/staging", "/tmp"}.issubset(mounts)
    env = {item["name"]: item.get("value") for item in container["env"]}
    assert env["SITULEARN_STAGING_DIR"] == "/staging"

    volumes = {
        volume["name"]: volume for volume in spec["template"]["spec"]["volumes"]
    }
    assert volumes["data"]["persistentVolumeClaim"]["claimName"] == "situlearn-data"
    assert volumes["staging"]["emptyDir"]["sizeLimit"] == "1Gi"
    assert "backup" not in volumes


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
    assert "OSS_ACCESS_KEY_ID" in secret["stringData"]
    assert "OSS_ACCESS_KEY_SECRET" in secret["stringData"]


def test_backup_cronjob_snapshots_database_to_oss():
    cronjob = _by_kind("CronJob")
    assert cronjob["spec"]["schedule"] == "17 3 * * *"
    assert cronjob["spec"]["concurrencyPolicy"] == "Forbid"
    container = cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"][
        "containers"
    ][0]
    assert container["image"] == "situlearn-web:0.2.2"
    assert container["command"][-1] == "situlearn.web.backup"
    assert "--keep-days" in container["args"]
    mounts = {mount["mountPath"] for mount in container["volumeMounts"]}
    assert "/data" in mounts
    assert "/backup" not in mounts
    env_sources = container["envFrom"]
    assert any("configMapRef" in item for item in env_sources)
    assert any("secretRef" in item for item in env_sources)


def test_network_policy_scopes_traffic():
    policy = _by_kind("NetworkPolicy")
    assert set(policy["spec"]["policyTypes"]) == {"Ingress", "Egress"}
    assert policy["spec"]["ingress"][0]["ports"][0]["port"] == 8000
    assert policy["spec"]["egress"][0]["ports"][0]["port"] == 53
    assert policy["spec"]["egress"][1]["to"][0]["ipBlock"]["cidr"] == "100.64.0.0/10"
    assert policy["spec"]["egress"][1]["ports"][0]["port"] == 443


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
    assert overlay["images"][0]["newTag"] == "0.2.2"
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
