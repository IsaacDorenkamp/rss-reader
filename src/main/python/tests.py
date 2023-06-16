import unittest
import models


class TestSubModel(models.JSONModel):
    _required = ('number',)
    number = int
    string = str


class TestModel(models.JSONModel):
    number = int
    string = str
    model_list = models.Multiple(TestSubModel)
    nested = models.Multiple(models.Multiple(int))


class ModelTests(unittest.TestCase):
    def _validate_test_model(self, model):
        self.assertEqual(model.number, 7)
        self.assertEqual(model.string, 'test')

        self.assertEqual(len(model.model_list), 1)
        self.assertEqual(model.model_list[0].number, 14)
        self.assertEqual(model.model_list[0].string, 'subtest')

        self.assertEqual(model.nested, ((1, 2), (3, 4), (5, 6)))

    def test_model_from_dict(self):
        source = {
            'number': 7,
            'string': 'test',
            'model_list': ({
                'number': 14,
                'string': 'subtest'
            },),
            'nested': [[1, 2], [3, 4], [5, 6]]
        }
        model = TestModel.from_dict(source)
        self._validate_test_model(model)

    def test_model_from_string(self):
        source = """{
    "number": 7,
    "string": "test",
    "model_list": [{
        "number": 14,
        "string": "subtest"
    }],
    "nested": [[1, 2], [3, 4], [5, 6]]
}"""
        model = TestModel.from_string(source)
        self._validate_test_model(model)

    def test_model_to_dict(self):
        model = TestModel(number=7, string="test", model_list=(TestSubModel(number=14, string="subtest"),),
                          nested=[[1, 2], [3, 4], [5, 6]])

        as_dict = model.to_dict()
        self.assertEqual(as_dict['number'], 7)
        self.assertEqual(as_dict['string'], 'test')

        self.assertEqual(len(as_dict['model_list']), 1)
        self.assertEqual(as_dict['model_list'][0]['number'], 14)
        self.assertEqual(as_dict['model_list'][0]['string'], 'subtest')

        self.assertEqual(as_dict['nested'], ((1, 2), (3, 4), (5, 6)))

    def test_model_required(self):
        with self.assertRaises(ValueError):
            TestSubModel.from_dict({'number': None, 'string': None})


if __name__ == '__main__':
    unittest.main()