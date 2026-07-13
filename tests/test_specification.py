import json
import math

import pytest

from eq_proof import InvalidSpecification, load_specification, parse_specification

BASE = {
    "schema_version": "1.0",
    "name": "valid",
    "variables": {"x": {}},
    "equations": [],
}


def changed(**updates):
    value = json.loads(json.dumps(BASE))
    value.update(updates)
    return value


@pytest.mark.parametrize(
    "document, message",
    [
        ([], "root"),
        (changed(schema_version="2.0"), "Unsupported"),
        (changed(name=""), "name"),
        (changed(description=3), "description"),
        (changed(metadata=[]), "metadata"),
        (changed(variables={}), "variables"),
        (changed(variables={"not valid": {}}), "variable name"),
        (changed(variables={"for": {}}), "variable name"),
        (changed(variables={"x": []}), "rule"),
        (changed(variables={"x": {"lower": True}}), "finite number"),
        (changed(variables={"x": {"lower": math.inf}}), "finite"),
        (changed(variables={"x": {"lower": 2, "upper": 1}}), "exceeds"),
        (changed(variables={"x": {"fixed": "yes"}}), "boolean"),
        (changed(variables={"x": {"unknown": 1}}), "Unknown variable"),
        (changed(equations={}), "array"),
        (changed(equations=["x == 1"]), "object"),
        (changed(equations=[{"id": "", "expression": "x == 1"}]), "id"),
        (changed(equations=[{"id": "a", "expression": ""}]), "non-empty expression"),
        (
            changed(
                equations=[
                    {"id": "a", "expression": "x == 1"},
                    {"id": "a", "expression": "x == 2"},
                ]
            ),
            "Duplicate",
        ),
        (changed(unknown=True), "Unknown root"),
    ],
)
def test_rejects_invalid_specifications(document, message):
    with pytest.raises(InvalidSpecification, match=message):
        parse_specification(document)


def test_parses_labels_units_and_descriptions():
    spec = parse_specification(
        {
            "schema_version": "1.0",
            "name": "labels",
            "variables": {"x": {"label": "Capacity", "unit": "FTE"}},
            "equations": [{"id": "cap", "expression": "x <= 10", "description": "Limit"}],
        }
    )
    assert spec.variables[0].label == "Capacity"
    assert spec.variables[0].unit == "FTE"
    assert spec.constraints[0].description == "Limit"


def test_load_specification_wraps_bad_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{")
    with pytest.raises(InvalidSpecification, match="Unable to read"):
        load_specification(path)
