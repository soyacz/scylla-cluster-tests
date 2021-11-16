from invoke import MockContext, Result
from tasks.sct import SCTSettings, create_sct_runner, Backends, TestDurationParams  # pylint: disable=import-error


class TestCreateSctRunner:

    def test_create_sct_runner_aws_runs_proper_hydra_command(self):  # pylint: disable=no-self-use
        expected_cmd = "./docker/env/hydra.sh create-runner-instance --cloud-provider aws --region eu-west-1" \
                       " --availability-zone a  --test-id UNIT_TEST --duration 10"
        ctx = MockContext(run={
            expected_cmd: Result()
        })
        SCTSettings(backend=Backends.AWS, test_name="unit_test", scylla_version="123",
                    test_config="config", test_id="UNIT_TEST")
        TestDurationParams(test_duration=10)
        create_sct_runner(ctx)

    def test_create_sct_runner_k8s_local_kind_aws_runs_proper_hydra_command(self):  # pylint: disable=no-self-use
        expected_cmd = "./docker/env/hydra.sh create-runner-instance --cloud-provider aws --region eu-west-1" \
                       " --availability-zone a --instance-type c5.xlarge --test-id UNIT_TEST --duration 10"
        ctx = MockContext(run={
            expected_cmd: Result()
        })
        SCTSettings(backend=Backends.K8S_LOCAL_KIND_AWS, test_name="unit_test", scylla_version="123",
                    test_config="config", test_id="UNIT_TEST")
        TestDurationParams(test_duration=10)

        create_sct_runner(ctx)

    def test_create_sct_runner_k8s_local_kind_gce_runs_proper_hydra_command(self):  # pylint: disable=no-self-use
        expected_cmd = "./docker/env/hydra.sh create-runner-instance --cloud-provider gce --region eu-west-1" \
                       " --availability-zone a --instance-type c5.xlarge --test-id UNIT_TEST --duration 10"
        ctx = MockContext(run={
            expected_cmd: Result()
        })
        SCTSettings(backend=Backends.K8S_LOCAL_KIND_GCE, test_name="unit_test", scylla_version="123",
                    test_config="config", test_id="UNIT_TEST")
        TestDurationParams(test_duration=10)
        create_sct_runner(ctx)
