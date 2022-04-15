# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright (c) 2022 ScyllaDB
import logging
from io import StringIO
import socket

from paramiko.client import SSHClient, AutoAddPolicy
from paramiko.rsakey import RSAKey

from sdcm.provision.user_data import CLOUD_INIT_SCRIPTS_PATH
from sdcm.utils.decorators import retrying

LOGGER = logging.getLogger(__name__)


class CloudInitError(Exception):
    pass


@retrying(n=120, sleep_time=5, allowed_exceptions=(OSError,))
def wait_for_ssh_port(host, port):
    socket.create_connection((host, port)).close()


def log_user_data_scripts_errors(ssh_client: SSHClient) -> bool:
    errors_found = False
    _, stdout, stderr = ssh_client.exec_command(f"ls {CLOUD_INIT_SCRIPTS_PATH}", timeout=10 * 60)
    ls_errors = stderr.read().decode()
    if ls_errors:
        LOGGER.error("Error listing generated scripts: %s", ls_errors)
        errors_found = True
    files_list = stdout.read().decode()
    if not files_list:
        LOGGER.error("No user data scripts were generated.")
        errors_found = True
    elif ".failed" in files_list:
        LOGGER.error("Some user data scripts have failed: %s", files_list)
        errors_found = True
    elif "done" not in files_list:
        LOGGER.error("User data scripts were not executed at all.")
        errors_found = True
    return errors_found


def wait_cloud_init_completes(instance: "VmInstance"):
    """Connects to VM with SSH and waits for cloud-init to complete. Verify if everything went ok.
    """
    LOGGER.info("Waiting for cloud-init to complete on node %s...", instance.name)
    with SSHClient() as ssh:
        errors_found = False
        ssh_key = RSAKey.from_private_key(StringIO(instance.ssh_private_key))
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        LOGGER.info("Waiting for ssh port to be open")
        wait_for_ssh_port(host=instance.public_ip_address, port=22)
        LOGGER.info("connecting with paramiko")
        ssh.connect(hostname=instance.public_ip_address, username=instance.user_name, pkey=ssh_key, timeout=5 * 60)
        LOGGER.info("paramiko connected. Waiting for cloud-init to finish")
        _, stdout, _ = ssh.exec_command("sudo cloud-init status --wait", timeout=10 * 60)
        status = stdout.read().decode()
        LOGGER.debug("cloud-init status: %s", status)
        if "done" not in status:
            LOGGER.error("Some error during cloud-init %s", status)
            errors_found = True
        scripts_errors_found = log_user_data_scripts_errors(ssh_client=ssh)
        if errors_found or scripts_errors_found:
            raise CloudInitError("Errors during cloud-init provisioning phase. See logs for errors.")
