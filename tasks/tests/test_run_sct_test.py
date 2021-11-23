from invoke import MockContext, Result
from tasks.sct import SCTSettings, Backends, TestDurationParams, \
    run_sct_test  # pylint: disable=import-error


class TestRunSctTest:  # pylint: disable=too-few-public-methods

    def test_run_sct_test_runs_proper_hydra_command(self):  # pylint: disable=no-self-use
        unlink_latest_cmd = "rm -fv ./latest"
        runner_ip_cmd = "cat sct_runner_ip||echo ''"
        expected_cmd = "./docker/env/hydra.sh --execute-on-runner 54.73.25.158 run-test pipeline_test --backend aws"
        ctx = MockContext(run={
            unlink_latest_cmd: Result(),
            runner_ip_cmd: Result(stdout="54.73.25.158"),
            expected_cmd: Result()
        })
        params = SCTSettings(backend=Backends.AWS, test_name="pipeline_test", scylla_version="123",
                             test_config="config", test_id="UNIT_TEST")
        duration = TestDurationParams(test_duration=10)
        run_sct_test(ctx, params=params, test_duration_params=duration)
