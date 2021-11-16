from invoke import MockContext, Result
from tasks.sct import get_test_duration, SCTSettings


def test_get_test_duration_adds_test_time_params_to_persisted_context():
    ctx = MockContext(run=Result("""target_upgrade_version: ''
                                test_duration: 240
                                test_id: 3f02ce37-1f92-4349-9c99-710595e9ebef
                                test_sst3: false
                                \n"""))
    ctx.persisted = SCTSettings(test_name="unit_test", scylla_version="123", test_config="config").dict()
    get_test_duration(ctx)
    assert "test_time_params" in ctx.persisted
    assert ctx.persisted.test_time_params["test_run_timeout"] == 300  # pylint: disable=no-member
    assert ctx.persisted.test_time_params["runner_timeout"] == 405  # pylint: disable=no-member
