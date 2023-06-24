import pytest

import models


class _TestSubModel(models.JSONModel):
    _required = ('number',)
    number = int
    string = str


class _TestModel(models.JSONModel):
    number = int
    string = str
    model_list = models.Multiple(_TestSubModel)
    nested = models.Multiple(models.Multiple(int))


def _validate_test_model(model):
    assert model.number == 7
    assert model.string == "test"

    assert len(model.model_list) == 1
    assert model.model_list[0].number == 14
    assert model.model_list[0].string == "subtest"

    assert model.nested == ((1, 2), (3, 4), (5, 6))

def test_model_from_dict():
    source = {
        'number': 7,
        'string': 'test',
        'model_list': ({
            'number': 14,
            'string': 'subtest'
        },),
        'nested': [[1, 2], [3, 4], [5, 6]]
    }
    model = _TestModel.from_dict(source)
    _validate_test_model(model)

def test_model_from_string():
    source = """{
    "number": 7,
    "string": "test",
    "model_list": [{
        "number": 14,
        "string": "subtest"
    }],
    "nested": [[1, 2], [3, 4], [5, 6]]
}"""
    model = _TestModel.from_string(source)
    _validate_test_model(model)

def test_model_to_dict():
    model = _TestModel(number=7, string="test", model_list=(_TestSubModel(number=14, string="subtest"),),
                        nested=[[1, 2], [3, 4], [5, 6]])

    as_dict = model.to_dict()

    assert as_dict["number"] == 7
    assert as_dict["string"] == "test"

    assert len(as_dict["model_list"]) == 1
    assert as_dict["model_list"][0]["number"] == 14
    assert as_dict["model_list"][0]["string"] == "subtest"

    assert as_dict["nested"] == ((1, 2), (3, 4), (5, 6))

def test_model_required():
    with pytest.raises(ValueError):
        _TestSubModel.from_dict({'number': None, 'string': None})
