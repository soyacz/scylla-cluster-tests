# pylint: disable=W,C,R
import os
from typing import List

from tasks.libs.config import Settings


class TestSettings:

    def test_settings_can_be_override_by_jenkins_params_env_var(self):
        os.environ["JENKINS_PARAMS"] = '[foo: im_foo, bar: 888, li:["val1", "val2"], cos: 44]'

        class TestSettings(Settings):
            foo: str
            bar: int
            li: List[str]

        settings = TestSettings()
        assert settings.foo == "im_foo"
        assert settings.bar == 888
        assert settings.li == ["val1", "val2"]

    def test_settings_can_be_override_by_env_file(self):
        with open('.env', "w") as f:
            f.write("foo=im_foo\n")
            f.write("bar=888\n")
            f.write("li=[val1, val2]")

        class TestSettings(Settings):
            foo: str
            bar: int
            li: List[str]

        settings = TestSettings()
        assert settings.foo == "im_foo"
        assert settings.bar == 888
        assert settings.li == ["val1", "val2"]
