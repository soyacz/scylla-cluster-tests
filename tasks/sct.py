# pylint: disable=W,C,R
import os
import re
from dataclasses import dataclass, asdict, field
from enum import Enum
from pprint import pprint
from typing import Union, List

from invoke import task, Collection
from pydantic import validator, BaseModel
from scylla_arms.config import Settings


def print_sct_env_vars(env):
    print([f"{k}={v}" for k, v in env.items() if k.startswith("SCT_")])


class Backends(str, Enum):
    aws: str = "aws"
    gce: str = "gce"
    aws_siren: str = "aws-siren"
    k8s_local_kind_aws: str = "k8s-local-kind-aws"
    k8s_eks: str = "k8s-eks"
    gce_siren: str = "gce-siren"
    k8s_local_kind_gce: str = "k8s-local-kind-gce"
    k8s_gke: str = "k8s-gke"
    k8s_gce_minikube: str = "k8s-gce-minikube"
    k8s_local_minikube: str = "k8s-local-minicube"
    k8s_local_kind: str = "k8s-local-kind"

    # def __str__(self):
    #     return self.value


class CloudProviders(str, Enum):
    aws: str = "aws"
    gce: str = "gce"
    azure: str = "azure"

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


class SCTSettings(Settings):
    backend: Backends = Backends.aws
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

    @validator('aws_region')
    def must_be_valid_region(cls, v):  # pylint: disable=no-self-argument
        valid_regions = ["us-east-1", "eu-west-1", "eu-west-2", "eu-north-1", "random"]
        if v not in valid_regions:
            raise ValueError(f"Unsupported region. Supported regions: {valid_regions}")
        if v == "random":
            return
        return v.title()

    class Config:
        env_file = '.longevity_env'
        env_file_encoding = 'utf-8'


def prepare_sct_env_variables(params):
    env = os.environ.copy()
    sct_params = ["k8s_scylla_operator_docker_image", "k8s_scylla_operator_helm_repo", "k8s_scylla_operator_chart_version"
                  "scylla_mgmt_agent_version"]
    env["CI"] = "true"
    env["SCT_CLUSTER_BACKEND"] = params.backend
    env["SCT_CONFIG_FILES"] = params.test_config
    for param in sct_params:
        if value := params.get(param):
            env["SCT_" + param.upper()] = str(value)
    return env


@task
def configure(ctx):
    settings = SCTSettings()
    test_id = os.getenv("SCT_TEST_ID")
    if not test_id:
        raise ValueError("Please provide SCT_TEST_ID env variable")
    ctx.persisted.update(test_id=test_id, **settings.dict())
    ctx.persisted.update()


@dataclass
class TestDurationParams:
    test_duration: int
    test_startup_timeout: int = 20
    test_teardown_timeout: int = 40
    collect_logs_timeout: int = 70
    resource_cleanup_timeout: int = 30
    send_email_timeout: int = 5
    test_run_timeout: int = field(init=False)
    runner_timeout: int = field(init=False)

    def __post_init__(self):
        self.test_run_timeout = self.test_startup_timeout + self.test_duration + self.test_teardown_timeout
        self.runner_timeout = sum([self.test_run_timeout, self.collect_logs_timeout, self.resource_cleanup_timeout,
                                   self.send_email_timeout])


@task
def get_test_duration(ctx):
    print("getting test time parameters")
    params = ctx.persisted
    env = prepare_sct_env_variables(params)
    print_sct_env_vars(env)
    print("getting configuration with hydra...", end=" ")
    out = ctx.run(
        f'./docker/env/hydra.sh output-conf -b {params.backend}', env=env, hide='out', timeout=60).stdout.strip()
    print("done")
    test_time_params = TestDurationParams(test_duration=int(re.search(r'test_duration: ([\d]+)', out).group(1)))
    ctx.persisted.test_time_params = asdict(test_time_params)
    pprint(f"test time parameters: \n {ctx.persisted.test_time_params}")


@task
def create_sct_runner(ctx, region):
    print("Creating SCT Runner...")
    params = ctx.persisted
    backend = Backends(params.backend)
    cloud_provider = CloudProviders.from_backend(backend)
    if cloud_provider not in ("aws", "gce"):
        print(f"Currently {cloud_provider} is not supported. Will run on regular builder")
    instance_type_arg = ""

    if backend == Backends.k8s_local_kind_aws:
        instance_type_arg = "--instance-type c5.xlarge"
    elif backend == Backends.k8s_local_kind_gce:
        instance_type_arg = "--instance-type c5.xlarge"
    ctx.run(" ".join(["./docker/env/hydra.sh", "create-runner-instance",
                      "--cloud-provider", cloud_provider,
                      "--region", region,
                      "--availability-zone",  params.availability_zone,
                      instance_type_arg if instance_type_arg else "",
                      "--test-id", params.test_id,
                      "--duration", str(params.test_time_params["test_duration"])]),
            timeout=5*60)
    print("SCT Runner created!")


@task(configure, get_test_duration)
def all_tasks(ctx):
    print("hello world!")
    print(f'params: {ctx.persisted.dict()=}')
    # print(f'param {ctx["params"]["aws_region"]=}')
