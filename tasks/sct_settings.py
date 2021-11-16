import uuid
from dataclasses import dataclass
from enum import Enum

from typing import Union, List
from pydantic import validator
from scylla_arms.config import ArmsSettings, PersistentModel


class Backends(str, Enum):
    AWS: str = "aws"
    GCE: str = "gce"
    AWS_SIREN: str = "aws-siren"
    K8S_LOCAL_KIND_AWS: str = "k8s-local-kind-aws"
    K8S_EKS: str = "k8s-eks"
    GCE_SIREN: str = "gce-siren"
    K8S_LOCAL_KIND_GCE: str = "k8s-local-kind-gce"
    K8S_GKE: str = "k8s-gke"
    K8S_GCE_MINIKUBE: str = "k8s-gce-minikube"
    K8S_LOCAL_MINIKUBE: str = "k8s-local-minicube"
    K8S_LOCAL_KIND: str = "k8s-local-kind"


class CloudProviders(str, Enum):
    AWS: str = "aws"
    GCE: str = "gce"
    AZURE: str = "azure"

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
    scylla_version: str
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
    email_recipients: str = "qa@scylladb.com"
    test_config: Union[str, List]
    test_name: str
    pytest_addopts: str = ""
    k8s_scylla_operator_helm_repo: str = "https://storage.googleapis.com/scylla-operator-charts/latest"
    k8s_scylla_operator_chart_version: str = "latest"
    k8s_scylla_operator_docker_image: str = ""
    test_id: str = str(uuid.uuid4())

    @validator('aws_region')
    def must_be_valid_region(cls, value):  # pylint: disable=no-self-argument, no-self-use
        valid_regions = ["us-east-1", "eu-west-1", "eu-west-2", "eu-north-1", "random"]
        if value not in valid_regions:
            raise ValueError(f"Unsupported region. Supported regions: {valid_regions}")
        if value == "random":
            return ""
        return value

    class Config:  # pylint: disable=too-few-public-methods
        env_file = '.longevity_env'
        env_file_encoding = 'utf-8'

    @property
    def builder(self) -> Builder:
        return Builder(self.backend, self.aws_region, self.gce_datacenter)


class TestDurationParams(PersistentModel):
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
