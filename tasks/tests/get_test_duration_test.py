from invoke import MockContext, Result
from tasks.sct import get_test_duration, SCTSettings, TestDurationParams  # pylint: disable=import-error


def test_get_test_duration_adds_test_time_params_to_persisted_context():
    ctx = MockContext(run=Result("""target_upgrade_version: ''
                                test_duration: 240
                                test_id: 3f02ce37-1f92-4349-9c99-710595e9ebef
                                test_sst3: false
                                \n"""))
    SCTSettings(test_name="unit_test", scylla_version="123", test_config="config")
    get_test_duration(ctx)
    test_time_params = TestDurationParams.load()
    assert test_time_params.test_run_timeout == 300  # pylint: disable=no-member
    assert test_time_params.runner_timeout == 405  # pylint: disable=no-member
