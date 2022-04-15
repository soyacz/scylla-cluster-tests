from sdcm.provision.common.configuration_script import SYSLOGNG_LOG_THROTTLE_PER_SECOND
from sdcm.sct_config import SCTConfiguration
from sdcm.sct_provision.instances_request_definition_builder import NodeTypeType
from sdcm.sct_provision.user_data_objects.syslog_ng import SyslogNgUserDataObject
from sdcm.test_config import TestConfig


def get_user_data_objects(test_config: TestConfig, sct_config: SCTConfiguration, instance_name: str, node_type: NodeTypeType):
    objects = [
        SyslogNgUserDataObject(logs_transport=sct_config.get('logs_transport'),
                               host_port=test_config.get_logging_service_host_port(),
                               throttle_per_second=SYSLOGNG_LOG_THROTTLE_PER_SECOND,
                               hostname=instance_name)
    ]
    match node_type:
        case "db":
            pass
    return objects
