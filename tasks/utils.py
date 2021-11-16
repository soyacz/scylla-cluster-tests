import os

from tasks.sct_settings import SCTSettings


def prepare_sct_env_variables(params: SCTSettings):
    env = os.environ.copy()
    sct_params = ["k8s_scylla_operator_docker_image", "k8s_scylla_operator_helm_repo",
                  "k8s_scylla_operator_chart_version"
                  "scylla_mgmt_agent_version"]
    env["CI"] = "true"
    env["SCT_CLUSTER_BACKEND"] = params.backend
    env["SCT_CONFIG_FILES"] = params.test_config
    for param in sct_params:
        if param in params:
            env["SCT_" + param.upper()] = str(getattr(params, param))
    return env
