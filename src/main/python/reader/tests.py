import unittest
import xml.etree.ElementTree as ETree

from .api import xml as xmlapi


# Test Entities
class XMLTestSubEntity(xmlapi.XMLEntityDef):
	key = xmlapi.XMLPrimitive('key', str)
	value = xmlapi.XMLPrimitive('value', str)


class XMLAttrEntry(xmlapi.XMLEntityDef):
	key = xmlapi.XMLAttribute('key', optional=False)
	value = xmlapi.XMLAttribute('value', optional=False)


class XMLTestEntity(xmlapi.XMLEntityDef):
	primitive = xmlapi.XMLPrimitive('string', str)
	numbers = xmlapi.XMLPrimitive('multiple', int, rule=xmlapi.XMLEntityRule.MULTIPLE)

	compound = xmlapi.XMLEntity('complex', XMLTestSubEntity)
	entries = xmlapi.XMLEntity('entry', XMLTestSubEntity, rule=xmlapi.XMLEntityRule.MULTIPLE)

	attr_entries = xmlapi.XMLEntity('attr-entry', XMLAttrEntry, rule=xmlapi.XMLEntityRule.MULTIPLE)

	text = xmlapi.XMLTextContent()


class ShortXMLTestEntity(xmlapi.XMLEntityDef):
	attr_entries = xmlapi.XMLEntity('attr-entry', XMLAttrEntry, rule=xmlapi.XMLEntityRule.MULTIPLE_OPTIONAL)
	entry = xmlapi.XMLEntity('entry', XMLTestSubEntity, rule=xmlapi.XMLEntityRule.SINGLE)


class XMLAPITests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		test_tree = ETree.fromstring("""
<root>
	first
	<string>primitive value</string>

	<multiple>1</multiple>
	<multiple>2</multiple>

	<complex>
		<key>test-key</key>
		<value>test-value</value>
	</complex>

	<entry>
		<key>test-key-1</key>
		<value>test-value-1</value>
	</entry>
	<entry>
		<key>test-key-2</key>
		<value>test-value-2</value>
	</entry>

	<attr-entry key="test-key-1" value="test-value-1" />
	<attr-entry key="test-key-2" value="test-value-2" />
	last
</root>
""")
		cls.structure = XMLTestEntity.from_xml(test_tree)

	def test_single_primitive(self):
		self.assertEqual(self.structure.primitive, "primitive value")

	def test_multiple_primitive(self):
		self.assertListEqual(self.structure.numbers, [1,2])

	def test_single_complex(self):
		compound = self.structure.compound
		self.assertEqual(compound.key, "test-key")
		self.assertEqual(compound.value, "test-value")

	def subtest_key_value(self, entries):
		self.assertEqual(len(entries), 2)

		self.assertEqual(entries[0].key, 'test-key-1')
		self.assertEqual(entries[0].value, 'test-value-1')
		self.assertEqual(entries[1].key, 'test-key-2')
		self.assertEqual(entries[1].value, 'test-value-2')

	def subtest_key_value_dict(self, entries):
		self.assertEqual(len(entries), 2)

		self.assertEqual(entries[0]['key'], 'test-key-1')
		self.assertEqual(entries[0]['value'], 'test-value-1')
		self.assertEqual(entries[1]['key'], 'test-key-2')
		self.assertEqual(entries[1]['value'], 'test-value-2')

	def test_multiple_complex(self):
		entries = self.structure.entries
		self.subtest_key_value(entries)

	def test_attributes(self):
		entries = self.structure.attr_entries
		self.subtest_key_value(entries)

	def test_text_content(self):
		text = self.structure.text

		self.assertEqual(len(text), 2)
		self.assertEqual(text[0], "first")
		self.assertEqual(text[1], "last")

	def test_attribute_fail(self):
		with self.assertRaises(xmlapi.XMLEntityAttributeError):
			ShortXMLTestEntity.from_string("""
<root>
	<entry>
		<key>key</key>
		<value>value</value>
	</entry>
	<attr-entry key="key" />
</root>
""")

	def test_missing_required(self):
		with self.assertRaises(xmlapi.XMLEntityConstraintError):
			ShortXMLTestEntity.from_string("""
<root>
	<attr-entry key="key" value="value" />
</root>
""")

	def test_too_many_elements(self):
		with self.assertRaises(xmlapi.XMLEntityConstraintError):
			ShortXMLTestEntity.from_string("""
<root>
	<entry>
		<key>key-1</key>
		<value>value-1</value>
	</entry>
	<entry>
		<key>key-2</key>
		<value>value-2</value>
	</entry>
</root>
""")

	def test_strict(self):
		with self.assertRaises(xmlapi.XMLEntityConstraintError):
			ShortXMLTestEntity.from_string("""
<root>
	<entry>
		<key>key</key>
		<value>value</value>
	</entry>
	<attr-entry key="key" value="value" />
	<unknown>not allowed</unknown>
</root>
""")

	def _test_numbers(self, numbers):
		self.assertEqual(len(numbers), 2)
		self.assertEqual(numbers[0], 1)
		self.assertEqual(numbers[1], 2)

	def _test_compound(self, compound):
		self.assertEqual(compound, {'key': 'test-key', 'value': 'test-value'})

	def test_to_dict(self):
		value = self.structure.to_dict()
		self.assertEqual(value['primitive'], 'primitive value')

		numbers = value['numbers']
		self._test_numbers(numbers)
		self._test_compound(value['compound'])

		self.subtest_key_value_dict(value['entries'])
		self.subtest_key_value_dict(value['attr_entries'])

		self.assertEqual(tuple(value['text']), ('first', 'last'))

	def test_from_dict(self):
		value = self.structure.to_dict()
		rebuilt = XMLTestEntity.from_dict(value)

		self.assertEqual(rebuilt.primitive, 'primitive value')

		numbers = rebuilt.numbers
		self.assertEqual(len(numbers), 2)
		self.assertEqual(numbers[0], 1)
		self.assertEqual(numbers[1], 2)

		compound = rebuilt.compound
		self.assertEqual(compound.key, 'test-key')
		self.assertEqual(compound.value, 'test-value')

		entries = rebuilt.entries
		self.subtest_key_value(entries)

		entries = rebuilt.attr_entries
		self.subtest_key_value(entries)

		self.assertEqual(tuple(rebuilt.text), ('first', 'last'))
