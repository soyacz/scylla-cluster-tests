import os

from sdcm.sct_config import SCTConfiguration
from tasks.sct_settings import SCTSettings, Backends


class TestSctSettings:

    def test_ami_id_db_scylla_desc_is_generated_from_git_branch_env_variable(self):  # pylint: disable=no-self-use
        os.environ["GIT_BRANCH"] = "origin/master"
        params = SCTSettings(scylla_version="4.5.1", test_config="path/to/test/config", test_name="test_name")

        assert params.ami_id_db_scylla_desc == "master"

    def test_env_property_generates_sct_env_variables_for_params_with_values(self):  # pylint: disable=no-self-use
        params = SCTSettings(backend=Backends.AWS, gce_datacenter="", availability_zone="b",
                             scylla_version="4.5.1", test_config="path/to/test/config", test_name="test_name",
                             tag_ami_with_result=False)

        env_vars = params.env

        assert env_vars["SCT_CLUSTER_BACKEND"] == "aws"
        assert env_vars["SCT_AVAILABILITY_ZONE"] == "b"
        assert env_vars["SCT_SCYLLA_VERSION"] == "4.5.1"
        assert env_vars["SCT_CONFIG_FILES"] == "path/to/test/config"
        assert "SCT_TEST_NAME" not in env_vars
        assert "SCT_TAG_AMI_WITH_RESULT" not in env_vars, "false values shouldn't be exported"
        assert "SCT_GCE_DATACENTER" not in env_vars, "empty values shouldn't be exported"

    def test_generated_sct_env_must_be_allowed(self):  # pylint: disable=no-self-use
        basic_params = dict(test_config="true", test_name="true", scylla_ami_id="true")
        all_params_with_value = {key: "true" for key, value in SCTSettings(**basic_params).dict().items() if not value}
        params2 = SCTSettings(**basic_params, **all_params_with_value)
        allowed_sct_env_vars = [option["env"] for option in SCTConfiguration.config_options]

        for param in params2.env:
            if param.startswith("SCT_"):
                assert param in allowed_sct_env_vars, f"{param} is not allowed as configuration opition"
