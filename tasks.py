import os

from invoke import task, Collection


# from rich import print  # pylint: disable=redefined-builtin
#
# @task
# def read_configuration(ctx):


@task()
def all_tasks(ctx):
    print("hello world!")
    print(ctx["params"])


ns = Collection(all_tasks)

ns.configure({'params': os.environ.get("JENKINS_PARAMS", "no jenkins params")})
