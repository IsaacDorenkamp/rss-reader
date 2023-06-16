from __future__ import annotations

import enum
import collections.abc
from typing import Dict, Any, TypeVar, Type
import xml.etree.ElementTree as ETree


# Utility functions
def type_string(types):
	if isinstance(types, type):
		return types.__name__
	else:
		return '(%s)' % ', '.join([t.__name__ for t in types])


def any_value(iterable):
	for item in iterable:
		if item:
			return item

	return None


def get_as(source, key, valid_types):
	value = source.get(key)
	if not isinstance(value, valid_types):
		raise TypeError("Expected type(s) %s for key '%s', got type %s" % (type_string(valid_types), key,
																		type_string(type(value))))
	else:
		return value


def get_as_iterable(source, key, valid_types):
	value = source.get(key)
	if not isinstance(value, collections.abc.Iterable):
		raise TypeError("Key '%s' does not refer to an iterable" % key)

	bad_type = any_value([None if isinstance(item, valid_types) else type(item).__name__ for item in value])
	if bad_type is None:
		return value
	else:
		raise TypeError("Expected list with item type %s, found item with type %s" % (type_string(valid_types), bad_type))


class XMLEntityError(Exception):
	def __init__(self, message):
		super().__init__(message)


class XMLEntityAttributeError(XMLEntityError):
	def __init__(self, message):
		super().__init__(message)


class XMLEntityValueError(XMLEntityError):
	def __init__(self, message):
		super().__init__(message)


class XMLEntityConstraintError(XMLEntityError):
	def __init__(self, message):
		super().__init__(message)


class XMLEntityRule(enum.Enum):
	SINGLE_OPTIONAL = 0
	SINGLE = 1
	MULTIPLE_OPTIONAL = 2
	MULTIPLE = 3

	def validate(self, value):
		if self == XMLEntityRule.SINGLE_OPTIONAL:
			return True
		elif self == XMLEntityRule.SINGLE:
			if value is None:
				raise XMLEntityConstraintError("%s cannot be None")
		elif self == XMLEntityRule.MULTIPLE_OPTIONAL:
			if not isinstance(value, collections.abc.Iterable):
				raise XMLEntityValueError("%s must be iterable")
		else:
			if not isinstance(value, collections.abc.Iterable):
				raise XMLEntityValueError("%s must be iterable")
			elif len(value) == 0:
				raise XMLEntityConstraintError("%s must not be empty")

	def get_default(self):
		if self in (XMLEntityRule.SINGLE_OPTIONAL, XMLEntityRule.SINGLE):
			return None
		else:
			return []

	def set_value(self, dct, key, value):
		if self in (XMLEntityRule.SINGLE_OPTIONAL, XMLEntityRule.SINGLE):
			if dct[key] is not None:
				raise XMLEntityConstraintError("Field '%s' cannot have more than one value." % key)
			else:
				dct[key] = value
		else:
			dct[key].append(value)

	def is_multiple(self):
		return self in [self.MULTIPLE, self.MULTIPLE_OPTIONAL]

	def is_single(self):
		return self in [self.SINGLE, self.SINGLE_OPTIONAL]


class XMLPrimitive:
	__xmltype__ = True

	def __init__(self, tag, processor, rule=XMLEntityRule.SINGLE):
		assert isinstance(tag, str), TypeError("tag must be a str")
		assert isinstance(rule, XMLEntityRule), TypeError("rule must be an XMLEntityRule")

		self.tag = tag
		self.rule = rule
		self.process = processor

	def from_xml(self, node, _=None):
		return self.process(node.text)


class XMLAttribute:
	__xmltype__ = True

	def __init__(self, attribute, optional=True, processor=None):
		assert isinstance(attribute, str), TypeError("attribute must be a str")
		assert isinstance(optional, bool), TypeError("optional must be a bool")
		assert callable(processor) or processor is None, TypeError("processor must be a callable or None")

		self.attribute = attribute
		self.optional = optional
		self.processor = processor

	def from_xml(self, node, _=None):
		if self.optional:
			raw = node.attrib.get(self.attribute)
		else:
			try:
				raw = node.attrib[self.attribute]
			except KeyError:
				raise XMLEntityAttributeError("Tag %s missing required attribute %s" % (node.tag, self.attribute))

		if self.processor is None:
			return raw
		else:
			return self.processor(raw)


class XMLTextContent:
	__xmltype__ = True

	@staticmethod
	def join(segments):
		return ''.join(segments)

	@staticmethod
	def primitive(segments):
		return segments[0] if len(segments) > 0 else ''

	def __init__(self, processor=None):
		assert callable(processor) or processor is None, TypeError("processor must be a callable or None")
		self.processor = processor

	def from_text(self, raw):
		if self.processor is None:
			return raw
		else:
			return self.processor(raw)


class XMLEntityMeta(type):
	def __new__(mcs, name, bases, dct):
		entity_type = super().__new__(mcs, name, bases, dct)

		if dct.get('abstract', False):
			del dct['abstract']
			return entity_type

		attributes = {}
		tag_types = {}
		text_handler = None
		for key, value in dct.items():
			is_xml_type = getattr(value, '__xmltype__', False)
			if is_xml_type:
				if isinstance(value, XMLAttribute):
					attributes[key] = value
				elif isinstance(value, XMLTextContent):
					if text_handler is not None:
						raise ValueError("XMLEntityDef subclasses must only have one XMLTextContent property.")
					else:
						text_handler = (key, value)
				else:
					tag_types[value.tag] = (key, value)

		entity_type.__xmlattributes__ = attributes
		entity_type.__xmltypes__ = tag_types
		entity_type.__xmltext__ = text_handler

		return entity_type


class XMLEntityDef(metaclass=XMLEntityMeta):
	abstract = True

	INCLUDE: Dict[str, str] = {}

	def __init__(self, **kw):
		for k, v in kw.items():
			setattr(self, k, v)

	@classmethod
	def from_string(cls, string, strict=True):
		tree = ETree.fromstring(string)
		return cls.from_xml(tree, strict=strict)

	@classmethod
	def from_xml(cls, node, strict=True):
		data = {entity_key: entity_value.rule.get_default() for entity_key, entity_value in
										cls.__xmltypes__.values()}

		# First, populate fields defined by attributes.
		for field, attribute in cls.__xmlattributes__.items():
			data[field] = attribute.from_xml(node)

		# Next, handle all tags.
		text = [node.text or '']

		for child in node:
			if child.tail is not None:
				text.append(child.tail)
			try:
				field, processor = cls.__xmltypes__[child.tag]
			except KeyError:
				if strict:
					raise XMLEntityConstraintError("Unexpected tag '%s' in parent node '%s'" % (child.tag, node.tag))
				else:
					continue

			processed = processor.from_xml(child, strict)
			processor.rule.set_value(data, field, processed)

		# Third, handle text content, if applicable.
		text = [item.strip() for item in text if item.strip() != '']
		if cls.__xmltext__ is not None:
			field, handler = cls.__xmltext__
			data[field] = handler.from_text(text)

		# Finally, run validation on data.
		for tag, pair in cls.__xmltypes__.items():
			field, processor = pair
			try:
				processor.rule.validate(data[field])
			except XMLEntityConstraintError as xmlerr:
				raise XMLEntityConstraintError(str(xmlerr) % field)

		return cls(**data)

	def to_dict(self) -> Dict[str, Any]:
		output = {}
		for field, processor in self.__xmltypes__.values():
			raw = getattr(self, field)
			if isinstance(processor, XMLEntity):
				if raw is None:
					assign = None
				else:
					if processor.rule.is_multiple():
						assign = tuple(item.to_dict() for item in raw)
					else:
						assign = raw.to_dict()
			else:
				assign = raw
			output[field] = assign

		for field in self.__xmlattributes__.keys():
			output[field] = getattr(self, field)

		if self.__xmltext__ is not None:
			field = self.__xmltext__[0]
			output[field] = getattr(self, field)

		for source, destination in self.INCLUDE.items():
			output[destination] = getattr(self, source, None)

		return output

	@classmethod
	def from_dict(cls, source: Dict[str, Any]) -> X:
		values = {}
		for key, processor in cls.__xmltypes__.values():
			try:
				value = source[key]
				processor.rule.validate(value)
				if isinstance(processor, XMLEntity):
					subtype = processor.type
					if value is None:
						values[key] = None
					else:
						if processor.rule.is_multiple():
							values[key] = list(subtype.from_dict(item) for item in value)
						else:
							values[key] = subtype.from_dict(value)
				else:
					try:
						values[key] = processor.process(value or '')
					except ValueError:
						values[key] = None
			except KeyError:
				raise ValueError("source missing expected key '%s'" % key)

		for key in cls.__xmlattributes__.keys():
			try:
				values[key] = source[key]
			except KeyError:
				raise ValueError("source missing expected key '%s'" % key)

		if cls.__xmltext__ is not None:
			key = cls.__xmltext__[0]
			try:
				values[key] = source[key]
			except KeyError:
				raise ValueError("source missing expected key '%s'" % key)

		for destination_key, source_key in cls.INCLUDE.items():
			values[destination_key] = source.get(source_key)

		return cls(**values)


X = TypeVar('X', bound=XMLEntityDef)


class XMLEntity:
	__xmltype__ = True

	def __init__(self, tag: str, subtype: Type[XMLEntityDef], rule: XMLEntityRule = XMLEntityRule.SINGLE):
		assert isinstance(tag, str), TypeError("tag should be a str")
		assert issubclass(subtype, XMLEntityDef), TypeError("subtype must be a subclass of XMLEntityDef")
		assert isinstance(rule, XMLEntityRule), TypeError("rule must be an instance of XMLEntityRule")

		self.tag = tag
		self.type = subtype
		self.rule = rule

	def from_xml(self, node, strict=True):
		return self.type.from_xml(node, strict=strict)
