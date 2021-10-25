# pylint: disable=W,C,R
import json

from tasks.libs.persisted_dicts import FilePersistedDotDict
import pytest


class TestFilePersistedDotDict:

    def test_attribute_can_be_set_and_is_saved_to_file(self, tmp_path):
        persist_file_path = tmp_path / "pfile"
        d = FilePersistedDotDict(persist_file_path)
        d.att = "test"

        assert d.att == "test"

        with open(persist_file_path, "r") as p_file:
            p = json.load(p_file)
            assert p["att"] == "test"

    def test_attribute_can_be_set_as_attribute_and_is_saved_to_file(self, tmp_path):
        persist_file_path = tmp_path / "pfile"
        d = FilePersistedDotDict(persist_file_path)
        d["att"] = "test"

        assert d.att == "test"

        with open(persist_file_path, "r") as p_file:
            p = json.load(p_file)
            assert p["att"] == "test"

    def test_attribute_can_be_deleted_and_is_saved_to_file(self, tmp_path):
        persist_file_path = tmp_path / "pfile"
        d = FilePersistedDotDict(persist_file_path)
        d.att = "test"

        del d.att

        with pytest.raises(AttributeError):
            d.att
        with open(persist_file_path, "r") as p_file:
            p = json.load(p_file)
            assert "att" not in p.keys()

    def test_all_attributes_can_be_cleared(self, tmp_path):
        persist_file_path = tmp_path / "pfile"
        d = FilePersistedDotDict(persist_file_path)
        d.att_a = "test"
        d.att_b = "test"

        d.clear()

        assert "att_a" not in d
        assert "att_b" not in d

        with open(persist_file_path, "r") as p_file:
            p = json.load(p_file)
            assert "att_a" not in p.keys()
            assert "att_b" not in p.keys()

    def test_can_update_multiple_attributes(self, tmp_path):
        persist_file_path = tmp_path / "pfile"
        d = FilePersistedDotDict(persist_file_path)
        d.att_a = "test"
        d.att_b = "test"

        d.update(att_a="new", att_c="test")

        assert d.att_a == "new"
        assert d.att_b == "test"
        assert d.att_c == "test"
