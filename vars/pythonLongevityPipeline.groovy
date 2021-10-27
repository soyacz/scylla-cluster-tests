#!groovy

def call(Map pipelineParams) {

    def builder = getJenkinsLabels(params.backend, params.aws_region, params.gce_datacenter)
    def functional_test = pipelineParams.functional_test

    pipeline {
        agent {
            label {
                   label 'aws-sct-builders-eu-west-1-new'
            }
        }
        environment {
            AWS_ACCESS_KEY_ID     = credentials('qa-aws-secret-key-id')
            AWS_SECRET_ACCESS_KEY = credentials('qa-aws-secret-access-key')
            SCT_TEST_ID = UUID.randomUUID().toString()
        }
        parameters {
            string(defaultValue: "${pipelineParams.get('backend', 'aws')}",
               description: 'aws|gce',
               name: 'backend')

            string(defaultValue: "${pipelineParams.get('aws_region', 'eu-west-1')}",
               description: 'Supported: us-east-1|eu-west-1|eu-west-2|eu-north-1|random (randomly select region)',
               name: 'aws_region')
            string(defaultValue: "${pipelineParams.get('gce_datacenter', 'us-east1')}",
                   description: 'GCE datacenter',
                   name: 'gce_datacenter')
            string(defaultValue: "a",
               description: 'Availability zone',
               name: 'availability_zone')

            string(defaultValue: '', description: '', name: 'scylla_ami_id')
            string(defaultValue: '', description: '', name: 'gce_image_db')

            string(defaultValue: '',
                   description: 'cloud path for RPMs, s3:// or gs://',
                   name: 'update_db_packages')
            string(defaultValue: '', description: '', name: 'scylla_version')
            string(defaultValue: '', description: '', name: 'scylla_repo')
            string(defaultValue: '', description: '', name: 'scylla_mgmt_agent_version')
            string(defaultValue: "${pipelineParams.get('scylla_mgmt_agent_address', '')}",
                   description: 'If empty - the default scylla manager agent repo will be taken',
                   name: 'scylla_mgmt_agent_address')
            string(defaultValue: "${pipelineParams.get('provision_type', 'spot')}",
                   description: 'spot|on_demand|spot_fleet',
                   name: 'provision_type')
            string(defaultValue: "${pipelineParams.get('instance_provision_fallback_on_demand', 'false')}",
                   description: 'true|false',
                   name: 'instance_provision_fallback_on_demand')

            string(defaultValue: "${pipelineParams.get('post_behavior_db_nodes', 'keep-on-failure')}",
                   description: 'keep|keep-on-failure|destroy',
                   name: 'post_behavior_db_nodes')
            string(defaultValue: "${pipelineParams.get('post_behavior_loader_nodes', 'destroy')}",
                   description: 'keep|keep-on-failure|destroy',
                   name: 'post_behavior_loader_nodes')
            string(defaultValue: "${pipelineParams.get('post_behavior_monitor_nodes', 'keep-on-failure')}",
                   description: 'keep|keep-on-failure|destroy',
                   name: 'post_behavior_monitor_nodes')
            string(defaultValue: "${pipelineParams.get('post_behavior_k8s_cluster', 'keep-on-failure')}",
                   description: 'keep|keep-on-failure|destroy',
                   name: 'post_behavior_k8s_cluster')

            string(defaultValue: "${pipelineParams.get('tag_ami_with_result', 'false')}",
                   description: 'true|false',
                   name: 'tag_ami_with_result')

            string(defaultValue: "${pipelineParams.get('ip_ssh_connections', 'private')}",
                   description: 'private|public|ipv6',
                   name: 'ip_ssh_connections')

            string(defaultValue: "${pipelineParams.get('manager_version', '')}",
                   description: 'master_latest|2.5|2.4|2.3',
                   name: 'manager_version')

            string(defaultValue: '',
                   description: 'If empty - the default manager version will be taken',
                   name: 'scylla_mgmt_address')

            string(defaultValue: "${pipelineParams.get('email_recipients', 'qa@scylladb.com')}",
                   description: 'email recipients of email report',
                   name: 'email_recipients')

            string(defaultValue: "${pipelineParams.get('test_config', '')}",
                   description: 'Test configuration file',
                   name: 'test_config')

            string(defaultValue: "${pipelineParams.get('test_name', '')}",
                   description: 'Name of the test to run',
                   name: 'test_name')

            string(defaultValue: "${pipelineParams.get('pytest_addopts', '')}",
                   description: (
                        '"pytest_addopts" is used by "run_pytest" hydra command. \n' +
                        'Useful for K8S functional tests which run using pytest. \n' +
                        'PyTest runner allows to provide any options using "PYTEST_ADDOPTS" ' +
                        'env var which gets set here if value is provided. \n' +
                        'Example: "--maxfail=1" - it will stop test run after first failure.'),
                   name: 'pytest_addopts')

            string(defaultValue: "${pipelineParams.get('k8s_scylla_operator_helm_repo', 'https://storage.googleapis.com/scylla-operator-charts/latest')}",
                   description: 'Scylla Operator helm repo',
                   name: 'k8s_scylla_operator_helm_repo')

            string(defaultValue: "${pipelineParams.get('k8s_scylla_operator_chart_version', 'latest')}",
                   description: 'Scylla Operator helm chart version',
                   name: 'k8s_scylla_operator_chart_version')

            string(defaultValue: "${pipelineParams.get('k8s_scylla_operator_docker_image', '')}",
                   description: 'Scylla Operator docker image',
                   name: 'k8s_scylla_operator_docker_image')

        }
    stages {
        stage('Prepare python') {
            steps {
                sh "pip3 install virtualenv"
                sh "python3 -m virtualenv poc-venv"
                sh "source poc-venv/bin/activate && pip3 install scylla-arms"
            }
        }
        stage('Checkout') {
                steps {
                    dir('scylla-cluster-tests') {
                        timeout(time: 5, unit: 'MINUTES') {
                            checkout scm

                            dir("scylla-qa-internal") {
                                git(url: 'git@github.com:scylladb/scylla-qa-internal.git',
                                    credentialsId:'b8a774da-0e46-4c91-9f74-09caebaea261',
                                    branch: 'master')
                            }
                        }
                    }
                }
            }
        stage('Get test duration') {
                steps {
                    catchError(stageResult: 'FAILURE') {
                        script {
                                dir('scylla-cluster-tests') {
                                    sh "JENKINS_PARAMS='${params}' ../poc-venv/bin/arms sct.configure sct.get-test-duration"
                            }
                        }
                    }
                }
            }
//         stage('Create SCT Runner') {
//                 steps {
//                     catchError(stageResult: 'FAILURE') {
//                         script {
//                             wrap([$class: 'BuildUser']) {
//                                 dir('scylla-cluster-tests') {
//                                     timeout(time: 5, unit: 'MINUTES') {
//                                         createSctRunner(params, runnerTimeout , builder.region)
//                                     }
//                                 }
//                             }
//                         }
//                     }
//                 }
//             }
        }
    }
//     post {
//         always {
//             archiveArtifacts artifacts: 'report.html, log.html, output.xml'
//         }
//     }
}
