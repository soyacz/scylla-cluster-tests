# pylint: disable=W,C,R
from enum import Enum
from time import sleep
from typing import List, Union

from invoke import task, Collection
from rich import print  # pylint: disable=redefined-builtin
from rich.console import Console

from tasks.libs.config import Settings

console = Console(color_system=None)


class Backends(str, Enum):
    aws: str = "aws"
    gce: str = "gce"


class SampleSettings(Settings):
    backend: Backends
    aws_region: Union[str, List]
    scylla_ami_id: str
    gce_image_db: str
    update_db_packages: str
    scylla_version: str
    scylla_repo: str
    scylla_mgmt_agent_version: str = ""
    scylla_mgmt_address: str


@task
def configure(ctx):
    print("preparing configuration")
    settings = SampleSettings()
    config = ctx.persisted
    print(settings.dict())
    config.update(**settings.dict())


@task
def clean(ctx):
    print("cleaning...")
    print(f"param from configuration: {ctx.persisted.aws_region}")
    ctx.run("ls test_lib")
    sleep(0.5)
    print("cleaning complete!")


@task
def build(ctx):
    print("started building...")
    print(f"Setting new context param 'something' to 'test'")
    ctx.persisted.something = "test"
    with open("build_output.txt", "w") as build_out_file:
        ctx.run("lscpu", out_stream=build_out_file)
    sleep(1)
    print("build complete!")


@task
def test(ctx):
    print("started tests...")
    print(f'Getting new context param "something": {ctx.persisted.something}')
    sleep(1)
    print("tests complete!")


@task
def package(ctx):
    print("started packaging...")
    sleep(1)
    print("packaging complete!")


@task(configure, clean, build, test, package)
def all_tasks(ctx):
    print("hello world!")


ns = Collection(all_tasks, configure, clean, build, test, package)
