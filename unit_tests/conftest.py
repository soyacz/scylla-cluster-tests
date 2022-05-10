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
# Copyright (c) 2020 ScyllaDB

import os
import logging
import collections
import re
from pathlib import Path
from typing import Optional, List, Dict, Pattern

import pytest
from invoke import Result

from sdcm import wait
from sdcm.cluster import BaseNode
from sdcm.prometheus import start_metrics_server
from sdcm.remote import RemoteCmdRunnerBase
from sdcm.remote.libssh2_client import StreamWatcher
from sdcm.utils.docker_remote import RemoteDocker

from unit_tests.dummy_remote import LocalNode, LocalScyllaClusterDummy

from unit_tests.lib.events_utils import EventsUtilsMixin


@pytest.fixture(scope='session')
def events():
    mixing = EventsUtilsMixin()
    mixing.setup_events_processes(events_device=True, events_main_device=False, registry_patcher=True)
    yield mixing

    mixing.teardown_events_processes()


@pytest.fixture(scope='session')
def prom_address():
    yield start_metrics_server()


@pytest.fixture(scope='session')
def docker_scylla():
    # make sure the path to the file is base on the host path, and not as the docker internal path i.e. /sct/
    # since we are going to mount it in a DinD (docker-inside-docker) setup
    base_dir = os.environ.get("_SCT_BASE_DIR", None)
    entryfile_path = Path(base_dir) if base_dir else Path(__file__).parent.parent
    entryfile_path = entryfile_path.joinpath('./docker/scylla-sct/entry.sh')

    alternator_flags = "--alternator-port 8000 --alternator-write-isolation=always"
    docker_version = "scylladb/scylla-nightly:666.development-0.20201015.8068272b466"
    cluster = LocalScyllaClusterDummy()
    scylla = RemoteDocker(LocalNode("scylla", cluster), image_name=docker_version,
                          command_line=f"--smp 1 --experimental 1 {alternator_flags}",
                          extra_docker_opts=f'-p 8000 -p 9042 --cpus="1" -v {entryfile_path}:/entry.sh --entrypoint'
                          f' /entry.sh')

    DummyRemoter = collections.namedtuple('DummyRemoter', 'run')
    scylla.remoter = DummyRemoter(run=scylla.run)

    def db_up():
        try:
            return scylla.is_port_used(port=BaseNode.CQL_PORT, service_name="scylla-server")
        except Exception as details:  # pylint: disable=broad-except
            logging.error("Error checking for scylla up normal: %s", details)
            return False

    def db_alternator_up():
        try:
            return scylla.is_port_used(port=8000, service_name="scylla-server")
        except Exception as details:  # pylint: disable=broad-except
            logging.error("Error checking for scylla up normal: %s", details)
            return False

    wait.wait_for(func=db_up, step=1, text='Waiting for DB services to be up', timeout=30, throw_exc=True)
    wait.wait_for(func=db_alternator_up, step=1, text='Waiting for DB services to be up alternator)',
                  timeout=30, throw_exc=True)

    yield scylla

    scylla.kill()


class FakeRemoter(RemoteCmdRunnerBase):
    """Fake remoter that responds to commands as described in `result_map` class attribute."""

    result_map: Dict[Pattern, Result] = {}

    def run(self,  # pylint: disable=too-many-arguments
            cmd: str,
            timeout: Optional[float] = None,
            ignore_status: bool = False,
            verbose: bool = True,
            new_session: bool = False,
            log_file: Optional[str] = None,
            retry: int = 1,
            watchers: Optional[List[StreamWatcher]] = None,
            change_context: bool = False
            ) -> Result:
        for pattern, result in self.result_map.items():
            if re.match(pattern, cmd) is not None:
                if ignore_status is True:
                    return result
                else:
                    if result.failed:
                        raise Exception(f"Exception occurred when running command: {cmd}")
                    return result
        raise ValueError(f"No fake result specified for command: {cmd}."
                         f"Set {self.__class__.__name__}.result_map variable with Dict[Pattern, Result] mapping")

    def _create_connection(self):
        pass

    def _close_connection(self):
        pass

    def is_up(self, timeout: float = 30):
        return True

    def _run_on_retryable_exception(self, exc: Exception, new_session: bool) -> bool:
        return True


@pytest.fixture
def fake_remoter():
    RemoteCmdRunnerBase.set_default_remoter_class(FakeRemoter)
    return FakeRemoter
