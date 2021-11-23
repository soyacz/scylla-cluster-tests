import os
import uuid
from dataclasses import dataclass
from enum import Enum

from typing import Union, List, Dict
from pydantic import validator, root_validator
from scylla_arms.config import ArmsSettings, PersistentModel


class Backends(str, Enum):
    AWS = "aws"
    GCE = "gce"
    AWS_SIREN = "aws-siren"
    K8S_LOCAL_KIND_AWS = "k8s-local-kind-aws"
    K8S_EKS = "k8s-eks"
    GCE_SIREN = "gce-siren"
    K8S_LOCAL_KIND_GCE = "k8s-local-kind-gce"
    K8S_GKE = "k8s-gke"
    K8S_GCE_MINIKUBE = "k8s-gce-minikube"
    K8S_LOCAL_MINIKUBE = "k8s-local-minicube"
    K8S_LOCAL_KIND = "k8s-local-kind"

    def __str__(self):
        return self.value


class CloudProviders(str, Enum):
    AWS = "aws"
    GCE = "gce"
    AZURE = "azure"

    @classmethod
    def from_backend(cls, backend: Union[Backends, str]):
        backend_providers = {
            "aws": "aws",
            "gce": "gce",
            "azure": "azure",
            "k8s-eks": "aws",
            "k8s-gke": "gce",
            "k8s-local-kind-aws": "aws",
            "k8s-local-kind-gce": "gce",
            "k8s-gce-minikube": "gce",
            "aws-siren": "aws",
            "gce-siren": "gce",
        }
        if isinstance(backend, Backends):
            provider = backend_providers[backend.value]
        else:
            provider = backend_providers[backend]
        return cls(provider)


@dataclass
class Builder:
    """TODO: add full implementation like in getJankinsLabels.groovy"""
    _backend: Backends
    _aws_region: str
    _gce_datacenter: str

    @property
    def region(self):
        return self._aws_region

    @property
    def label(self):
        jenkins_labels: dict[str, str] = {'aws-eu-west-1': 'aws-sct-builders-eu-west-1-new',
                                          'aws-eu-west-2': 'aws-sct-builders-eu-west-2',
                                          'aws-eu-north-1': 'aws-sct-builders-eu-north-1',
                                          'aws-eu-central-1': 'aws-sct-builders-eu-central-1',
                                          'aws-us-east-1': 'aws-sct-builders-us-east-1-new',
                                          'gce-us-east1': 'gce-sct-builders-us-east1',
                                          'gce-us-west1': 'gce-sct-builders-us-west1',
                                          'gce': 'gce-sct-builders',
                                          'docker': 'sct-builders'}
        return jenkins_labels[f"aws-{self._aws_region}"]


class SCTSettings(ArmsSettings):
    backend: Backends = Backends.AWS
    aws_region: Union[str, List] = "eu-west-1"
    gce_datacenter: str = "us-east1"
    availability_zone: str = "a"
    scylla_ami_id: str = ""
    gce_image_db: str = ""
    update_db_packages: str = ""
    scylla_version: str = ""
    new_version: str = ""
    scylla_repo: str = ""
    scylla_mgmt_agent_version: str = ""
    scylla_mgmt_agent_address: str = ""
    provision_type: str = "spot"
    instance_provision_fallback_on_demand: bool = False
    post_behavior_db_nodes: str = "keep-on-failure"
    post_behavior_loader_nodes: str = "destroy"
    post_behavior_monitor_nodes: str = "keep-on-failure"
    post_behavior_k8s_cluster: str = "keep-on-failure"
    tag_ami_with_result: bool = False
    ip_ssh_connections: str = "private"
    manager_version: str = ""
    scylla_mgmt_address: str = ""
    email_recipients: Union[str, List] = "qa@scylladb.com"
    test_config: Union[str, List]
    test_name: str
    pytest_addopts: str = ""
    k8s_scylla_operator_helm_repo: str = "https://storage.googleapis.com/scylla-operator-charts/latest"
    k8s_scylla_operator_chart_version: str = "latest"
    k8s_scylla_operator_docker_image: str = ""
    k8s_scylla_operator_upgrade_docker_image: str = ""
    k8s_scylla_operator_upgrade_helm_repo: str = ""
    k8s_scylla_operator_upgrade_chart_version: str = ""
    oracle_scylla_version: str = ""
    gemini_seed: str = ""
    ami_id_db_scylla_desc: str = ""
    test_id: str = str(uuid.uuid4())
    functional_test: bool = False

    class Config:  # pylint: disable=too-few-public-methods
        env_file = '.longevity_env'
        env_file_encoding = 'utf-8'

    @root_validator
    def version(cls, values):  # pylint: disable=no-self-argument, no-self-use
        scylla_ami_id = values.pop("scylla_ami_id")
        values["scylla_ami_id"] = ""
        gce_image_db = values.pop("gce_image_db")
        values["gce_image_db"] = ""
        scylla_version = values.pop("scylla_version")
        values["scylla_version"] = ""
        scylla_repo = values.pop("scylla_repo")
        values["scylla_repo"] = ""
        if scylla_ami_id:
            values["scylla_ami_id"] = scylla_ami_id
        elif gce_image_db:
            values["gce_image_db"] = gce_image_db
        elif scylla_version:
            values["scylla_version"] = scylla_version
        elif scylla_repo:
            values["scylla_repo"] = scylla_repo
        elif "k8s" in str(values.get("backend")):
            print("Kubernetes backend with empty scylla version: version will be taken from scylla helm chart.")
        else:
            raise ValueError("need to choose one of: scylla_ami_id, gce_image_db, scylla_version, scylla_repo")
        return values

    @validator('aws_region')
    def must_be_valid_region(cls, value):  # pylint: disable=no-self-argument, no-self-use
        valid_regions = ["us-east-1", "eu-west-1", "eu-west-2", "eu-north-1", "random"]
        if value not in valid_regions:
            raise ValueError(f"Unsupported region. Supported regions: {valid_regions}")
        if value == "random":
            return ""
        return value

    @validator("ami_id_db_scylla_desc")
    def ami_id_desc(cls, value):  # pylint: disable=no-self-argument, no-self-use
        if git_branch := os.getenv("GIT_BRANCH"):
            return git_branch.replace(
                "origin/branch-", "").replace("origin/", "").replace(".", "-").replace("_", "-")[:8]
        else:
            return value

    @property
    def builder(self) -> Builder:
        return Builder(self.backend, self.aws_region, self.gce_datacenter)

    @property
    def env(self) -> Dict[str, str]:
        env = {}
        params = self.dict()
        params.pop("test_name")
        params.pop("functional_test")
        env["CI"] = "true"
        env["SCT_CLUSTER_BACKEND"] = params.pop("backend")
        env["SCT_CONFIG_FILES"] = params.pop("test_config")
        env["SCT_COLLECT_LOGS"] = "false"
        if self.aws_region:
            params.pop("aws_region")
            env["SCT_REGION_NAME"] = self.aws_region
        if self.provision_type:
            params.pop("provision_type")
            env["SCT_INSTANCE_PROVISION"] = self.provision_type
        if self.pytest_addopts:
            params.pop("pytest_addopts")
            env["PYTEST_ADDOPTS"] = self.pytest_addopts
        if self.scylla_ami_id:
            params.pop("scylla_ami_id")
            env["SCT_AMI_ID_DB_SCYLLA"] = self.scylla_ami_id
        for param, value in params.items():
            if value:
                env["SCT_" + param.upper()] = str(value)
        return env


class TestDurationParams(PersistentModel):
    """Time parameters for test execution. All values are in minutes"""

    test_duration: int
    test_startup_timeout: int = 20
    test_teardown_timeout: int = 40
    collect_logs_timeout: int = 70
    resource_cleanup_timeout: int = 30
    send_email_timeout: int = 5

    @property
    def test_run_timeout(self):
        return self.test_startup_timeout + self.test_duration + self.test_teardown_timeout

    @property
    def runner_timeout(self):
        return sum([self.test_run_timeout, self.collect_logs_timeout, self.resource_cleanup_timeout,
                    self.send_email_timeout])
