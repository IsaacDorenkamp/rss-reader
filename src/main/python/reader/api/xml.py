import enum
import collections.abc

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
		raise TypeError("Expected type(s) %s for key '%s', got type %s" % (type_string(valid_types), key, type_string(type(value))))
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

class XMLPrimitive:
	__xmltype__ = True

	def __init__(self, tag, primitive_type, rule=XMLEntityRule.SINGLE):
		assert isinstance(tag, str), TypeError("tag must be a str")
		assert isinstance(rule, XMLEntityRule), TypeError("rule must be an XMLEntityRule")

		self.tag = tag
		self.rule = rule
		self.primitive = primitive_type

	def from_xml(self, node, _=None):
		return self.primitive(node.text)

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

	join = lambda segments: ''.join(segments)
	primitive = lambda segments: segments[0] if len(segments) > 0 else ''

	def __init__(self, processor=None):
		assert callable(processor) or processor is None, TypeError("processor must be a callable or None")
		self.processor = processor

	def from_text(self, raw):
		if self.processor is None:
			return raw
		else:
			return self.processor(raw)

class XMLEntityMeta(type):
	def __new__(cls, name, bases, dct):
		entity_type = super().__new__(cls, name, bases, dct)

		if dct.get('abstract', False):
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

		def from_xml(node, strict=True):
			data = { key: value.rule.get_default() for key, value in entity_type.__xmltypes__.values() }

			# First, populate fields defined by attributes.
			for field, attribute in entity_type.__xmlattributes__.items():
				data[field] = attribute.from_xml(node)

			# Next, handle all tags.
			text = [node.text or '']

			for child in node:
				if child.tail is not None:
					text.append(child.tail)
				try:
					field, processor = entity_type.__xmltypes__[child.tag]
				except KeyError:
					if strict:
						raise XMLEntityConstraintError("Unexpected tag '%s' in parent node '%s'" % (child.tag, node.tag))
					else:
						continue

				value = processor.from_xml(child, strict)
				processor.rule.set_value(data, field, value)

			# Third, handle text content, if applicable.
			text = [item.strip() for item in text if item.strip() != '']
			if entity_type.__xmltext__ is not None:
				field, handler = entity_type.__xmltext__
				data[field] = handler.from_text(text)

			# Finally, run validation on data.
			for tag, pair in entity_type.__xmltypes__.items():
				field, processor = pair
				try:
					processor.rule.validate(data[field])
				except XMLEntityConstraintError as xmlerr:
					raise XMLEntityConstraintError(str(xmlerr) % field)

			return entity_type(**data)

		def from_string(cls, string, strict=True):
			tree = ETree.fromstring(string)
			return cls.from_xml(tree, strict=strict)

		custom_constructor = dct.get('__init__', None)
		def constructor(self, *args, **kw):
			for key, value in kw.items():
				setattr(self, key, value)

			if custom_constructor is not None:
				custom_constructor(self, *args, **kw)

		entity_type.from_xml = staticmethod(from_xml)
		entity_type.from_string = classmethod(from_string)
		entity_type.__init__ = constructor

		return entity_type

class XMLEntityDef(metaclass=XMLEntityMeta):
	abstract = True

class XMLEntity:
	__xmltype__ = True

	def __init__(self, tag, subtype, rule=XMLEntityRule.SINGLE):
		assert isinstance(tag, str), TypeError("tag should be a str")
		assert issubclass(subtype, XMLEntityDef), TypeError("subtype must be a subclass of XMLEntityDef")
		assert isinstance(rule, XMLEntityRule), TypeError("rule must be an instance of XMLEntityRule")

		self.tag = tag
		self.type = subtype
		self.rule = rule

	def from_xml(self, node, strict=True):
		return self.type.from_xml(node, strict=strict)