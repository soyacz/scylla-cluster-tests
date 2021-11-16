from dataclasses import asdict

from invoke import MockContext, Result
from tasks.sct import SCTSettings, create_sct_runner, Backends, TestDurationParams


class TestCreateSctRunner:

    def test_create_sct_runner_aws_runs_proper_hydra_command(self):  # pylint: disable=no-self-use
        expected_cmd = "./docker/env/hydra.sh create-runner-instance --cloud-provider aws --region region" \
                       " --availability-zone a  --test-id UNIT_TEST --duration 10"
        ctx = MockContext(run={
            expected_cmd: Result()
        })
        ctx.persisted = SCTSettings(backend=Backends.aws, test_name="unit_test", scylla_version="123",
                                    test_config="config").dict()
        ctx.persisted.test_time_params = asdict(TestDurationParams(test_duration=10))
        ctx.persisted.test_id = "UNIT_TEST"
        create_sct_runner(ctx, region="region")

    def test_create_sct_runner_k8s_local_kind_aws_runs_proper_hydra_command(self):  # pylint: disable=no-self-use
        expected_cmd = "./docker/env/hydra.sh create-runner-instance --cloud-provider aws --region region" \
                       " --availability-zone a --instance-type c5.xlarge --test-id UNIT_TEST --duration 10"
        ctx = MockContext(run={
            expected_cmd: Result()
        })
        ctx.persisted = SCTSettings(backend=Backends.k8s_local_kind_aws, test_name="unit_test", scylla_version="123",
                                    test_config="config").dict()
        ctx.persisted.test_time_params = asdict(TestDurationParams(test_duration=10))
        ctx.persisted.test_id = "UNIT_TEST"
        create_sct_runner(ctx, region="region")

    def test_create_sct_runner_k8s_local_kind_gce_runs_proper_hydra_command(self):  # pylint: disable=no-self-use
        expected_cmd = "./docker/env/hydra.sh create-runner-instance --cloud-provider gce --region region" \
                       " --availability-zone a --instance-type c5.xlarge --test-id UNIT_TEST --duration 10"
        ctx = MockContext(run={
            expected_cmd: Result()
        })
        ctx.persisted = SCTSettings(backend=Backends.k8s_local_kind_gce, test_name="unit_test", scylla_version="123",
                                    test_config="config").dict()
        ctx.persisted.test_time_params = asdict(TestDurationParams(test_duration=10))
        ctx.persisted.test_id = "UNIT_TEST"
        create_sct_runner(ctx, region="region")
