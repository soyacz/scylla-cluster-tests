import os

from invoke import task, Collection


from rich import print  # pylint: disable=redefined-builtin
from rich.console import Console
console = Console(color_system=None)

# console.color_system = None
#
# @task
# def read_configuration(ctx):


@task()
def all_tasks(ctx):
    print("hello world!")
    print(ctx["params"])
    console.print(os.environ)


ns = Collection(all_tasks)

ns.configure({'params': os.environ.get("JENKINS_PARAMS", "no jenkins params")})
