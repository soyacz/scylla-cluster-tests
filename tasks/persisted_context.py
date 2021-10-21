# pylint: disable=W,C,R
import json
import os
import re
from collections import namedtuple


class PersistedContext:
    _persist_file_path = "persisted_params.json"

    def __init__(self):
        if os.path.exists(self._persist_file_path):
            with open(self._persist_file_path, "r") as persist_file:
                params = json.load(persist_file)
                self.params = params["params"]
        else:
            self.params = self._parse_jenkins_params()
            self.save()

    def save(self):
        with open(self._persist_file_path, "w") as persist_file:
            persist_file.write(json.dumps({"params": self.params}, indent=2))

    def _parse_jenkins_params(self):
        raw_jenkins_params = os.getenv("JENKINS_PARAMS")[1:-1]
        list_params = re.compile(r"(\w+):(\[[^]]+\])")
        scalar_params = re.compile(r"(\w+):([^,]*)")
        parsed_params = dict(scalar_params.findall(raw_jenkins_params))
        for k, v in list_params.findall(raw_jenkins_params):
            parsed_params[k] = json.loads(v)
        return parsed_params

    @staticmethod
    def _to_named_tuple(name, dictionary):
        return namedtuple(name, field_names=dictionary.keys())(**dictionary)
