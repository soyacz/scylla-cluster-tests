# pylint: disable=W,C,R
from time import sleep

from invoke import task, Collection


from rich import print  # pylint: disable=redefined-builtin
from rich.console import Console

from tasks.persisted_context import PersistedContext

console = Console(color_system=None)


@task
def clean(ctx):
    print("cleaning...")
    ctx.run("ls test_lib")
    sleep(0.5)
    print("cleaning complete!")


@task
def build(ctx):
    print("started building...")
    print(f"Setting new context param 'something' to 'test'")
    ctx.persisted.params["something"] = "test"
    with open("build_output.txt", "w") as build_out_file:
        ctx.run("lscpu", out_stream=build_out_file)
    sleep(1)
    ctx.persisted.save()
    print("build complete!")


@task
def test(ctx):
    print("started tests...")
    print(f'Getting new context param "something": {ctx.persisted.params["something"]}')
    sleep(1)
    print("tests complete!")


@task
def package(ctx):
    print("started packaging...")
    sleep(1)
    print("packaging complete!")


@task(clean, build, test, package)
def all_tasks(ctx):
    print("hello world!")
    print(f'jenkins params: {ctx.persisted.params=}')
    # print(f'param {ctx["params"]["aws_region"]=}')
    ctx["persisted"].save()


ns = Collection(all_tasks, clean, build, test, package)
