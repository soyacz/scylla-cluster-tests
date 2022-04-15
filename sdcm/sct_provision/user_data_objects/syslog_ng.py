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
from dataclasses import dataclass
from typing import Tuple

from sdcm.provision.common.utils import configure_syslogng_target_script, restart_syslogng_service
from sdcm.provision.user_data import UserDataObject


@dataclass
class SyslogNgUserDataObject(UserDataObject):
    logs_transport: str
    host_port: Tuple[str, int]
    throttle_per_second: int
    hostname: str = ""

    @property
    def is_applicable(self) -> bool:
        return self.logs_transport == 'syslog-ng'

    @property
    def packages(self) -> set[str]:
        return {"syslog-ng"}

    @property
    def script(self) -> str:
        script = configure_syslogng_target_script(host=self.host_port[0],
                                                  port=self.host_port[1],
                                                  throttle_per_second=self.throttle_per_second,
                                                  hostname=self.hostname)
        script += restart_syslogng_service()
        return script
