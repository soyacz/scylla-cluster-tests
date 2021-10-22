# pylint: disable=W,C,R
import os
import re

from invoke import task, Collection
from rich import print  # pylint: disable=redefined-builtin
from rich.console import Console
console = Console(color_system=None)


def print_sct_env_vars(env):
    print([f"{k}={v}" for k, v in env.items() if k.startswith("SCT_")])


def prepare_sct_env_variables(params):
    env = os.environ.copy()
    env["CI"] = "true"
    env["SCT_CLUSTER_BACKEND"] = params["backend"]
    env["SCT_CONFIG_FILES"] = str(params["test_config"])
    if par := params.get("k8s_scylla_operator_docker_image"):
        env["SCT_K8S_SCYLLA_OPERATOR_DOCKER_IMAGE"] = str(par)
    if par := params.get("k8s_scylla_operator_helm_repo"):
        env["SCT_K8S_SCYLLA_OPERATOR_HELM_REPO"] = str(par)
    if par := params.get("k8s_scylla_operator_chart_version"):
        env["SCT_K8S_SCYLLA_OPERATOR_CHART_VERSION"] = str(par)
    if par := params.get("scylla_mgmt_agent_version"):
        env["SCT_SCYLLA_MGMT_AGENT_VERSION"] = str(par)
    return env


@task
def get_test_duration(ctx):
    print("getting test time parameters")
    print(ctx.persisted.params)
    params = ctx.persisted.params
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
    ctx.persisted.params["test_time_params"] = t_par
    print(f"test time parameters: \n {t_par}")
    ctx.persisted.save()


@task(get_test_duration)
def all_tasks(ctx):
    print("hello world!")
    print(f'params: {ctx.persisted.params=}')
    # print(f'param {ctx["params"]["aws_region"]=}')
    ctx["persisted"].save()


ns = Collection(all_tasks, get_test_duration)
