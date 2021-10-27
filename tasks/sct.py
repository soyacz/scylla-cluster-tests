# pylint: disable=W,C,R
import os
import re
from enum import Enum
from typing import Union, List

from invoke import task, Collection
from pydantic import validator
from scylla_arms.config import Settings


def print_sct_env_vars(env):
    print([f"{k}={v}" for k, v in env.items() if k.startswith("SCT_")])


class Backends(str, Enum):
    aws: str = "aws"
    gce: str = "gce"


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
    def must_be_valid_region(self, v):
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
    ctx.persisted.update(**settings.dict())


@task
def get_test_duration(ctx):
    print("getting test time parameters")
    params = ctx.persisted
    env = prepare_sct_env_variables(params)
    print_sct_env_vars(env)
    out = ctx.run(
        f'./docker/env/hydra.sh output-conf -b {params["backend"]}', env=env, hide='out', timeout=60).stdout.strip()
    t_par = {
        "test_duration": int(re.search(r'test_duration: ([\d]+)', out).group(1)),
        "test_startup_timeout": 20,
        "test_teardown_timeout": 40,
        "collect_logs_timeout": 70,
        "resource_cleanup_timeout": 30,
        "send_email_timeout": 5,
    }
    t_par["test_run_timeout"] = t_par["test_startup_timeout"] + t_par["test_duration"] + t_par["test_teardown_timeout"]
    t_par["runner_timeout"] = t_par["test_run_timeout"] + t_par["collect_logs_timeout"] + \
        t_par["resource_cleanup_timeout"] + t_par["send_email_timeout"]
    ctx.persisted.test_time_params = t_par
    print(f"test time parameters: \n {t_par}")


@task(configure, get_test_duration)
def all_tasks(ctx):
    print("hello world!")
    print(f'params: {ctx.persisted.dict()=}')
    # print(f'param {ctx["params"]["aws_region"]=}')
