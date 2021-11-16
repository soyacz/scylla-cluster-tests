# pylint: disable=W,C,R
import re
from pprint import pprint

from invoke import task
from scylla_arms.config import inject_persistent_models
from tasks.sct_settings import SCTSettings, TestDurationParams, Backends, CloudProviders
from tasks.utils import prepare_sct_env_variables


def print_sct_env_vars(env):
    print([f"{k}={v}" for k, v in env.items() if k.startswith("SCT_")])


@task
def configure(ctx):
    sett = SCTSettings()
    print("SCT Settings:")
    pprint(sett.dict())


@task
@inject_persistent_models
def get_test_duration(ctx, params: SCTSettings):
    print("getting test time parameters")
    env = prepare_sct_env_variables(params)
    print_sct_env_vars(env)
    print("getting configuration with hydra...", end=" ")
    out = ctx.run(
        f'./docker/env/hydra.sh output-conf -b {params.backend}', env=env, hide='out', timeout=60).stdout.strip()
    print("done")
    test_time_params = TestDurationParams(test_duration=int(re.search(r'test_duration: ([\d]+)', out).group(1)))
    pprint(f"test time parameters: \n {test_time_params}")


@task
@inject_persistent_models
def create_sct_runner(ctx, params: SCTSettings, test_duration_params: TestDurationParams):
    print("Creating SCT Runner...")
    backend = Backends(params.backend)
    cloud_provider = CloudProviders.from_backend(backend)
    env = prepare_sct_env_variables(params)
    if cloud_provider not in ("aws", "gce"):
        print(f"Currently {cloud_provider} is not supported. Will run on regular builder")
    instance_type_arg = ""

    if backend == Backends.K8S_LOCAL_KIND_AWS:
        instance_type_arg = "--instance-type c5.xlarge"
    elif backend == Backends.K8S_LOCAL_KIND_GCE:
        instance_type_arg = "--instance-type c5.xlarge"
    ctx.run(" ".join(["./docker/env/hydra.sh", "create-runner-instance",
                      "--cloud-provider", cloud_provider,
                      "--region", params.builder.region,
                      "--availability-zone", params.availability_zone,
                      instance_type_arg if instance_type_arg else "",
                      "--test-id", params.test_id,
                      "--duration", str(test_duration_params.test_duration)]),
            timeout=5 * 60,
            env=env)
    print("SCT Runner created!")


@task(configure, get_test_duration, create_sct_runner)
def all_tasks(ctx):
    print("All tasks completed successfully")
