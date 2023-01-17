import xml.etree.ElementTree as ETree

from .xml import *

class Category(XMLEntityDef):
	domain = XMLAttribute('domain')
	value = XMLTextContent(XMLTextContent.primitive)

class Cloud(XMLEntityDef):
	domain = XMLAttribute('domain')
	path = XMLAttribute('path')
	port = XMLAttribute('port')
	protocol = XMLAttribute('protocol')
	register_procedure = XMLAttribute('registerProcedure')

class Image(XMLEntityDef):
	link = XMLPrimitive('link', str, rule=XMLEntityRule.SINGLE)
	title = XMLPrimitive('title', str, rule=XMLEntityRule.SINGLE)
	url = XMLPrimitive('url', str, rule=XMLEntityRule.SINGLE)
	description = XMLPrimitive('description', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	height = XMLPrimitive('height', int, rule=XMLEntityRule.SINGLE_OPTIONAL)
	width = XMLPrimitive('width', int, rule=XMLEntityRule.SINGLE_OPTIONAL)

class Item(XMLEntityDef):
	class Enclosure(XMLEntityDef):
		length = XMLAttribute('length', optional=False, processor=lambda x: int(x))
		type = XMLAttribute('type', optional=False)
		url = XMLAttribute('url', optional=False)

	class GUID(XMLEntityDef):
		is_permalink = XMLAttribute('isPermaLink')
		value = XMLTextContent(XMLTextContent.primitive)

	class Source(XMLEntityDef):
		url = XMLAttribute('url', optional=False)
		value = XMLTextContent(XMLTextContent.primitive)

	author = XMLPrimitive('author', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	category = XMLEntity('category', Category, rule=XMLEntityRule.MULTIPLE_OPTIONAL)
	comments = XMLPrimitive('comments', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	description = XMLPrimitive('description', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	enclosure = XMLEntity('enclosure', Enclosure, rule=XMLEntityRule.MULTIPLE_OPTIONAL)
	link = XMLPrimitive('link', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	pub_date = XMLPrimitive('pubDate', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	source = XMLEntity('source', Source, rule=XMLEntityRule.SINGLE_OPTIONAL)
	title = XMLPrimitive('title', str, rule=XMLEntityRule.SINGLE_OPTIONAL)

class Channel(XMLEntityDef):
	class SkipDays(XMLEntityDef):
		days = XMLPrimitive('day', str, rule=XMLEntityRule.MULTIPLE)

	class SkipHours(XMLEntityDef):
		hours = XMLPrimitive('hour', int, rule=XMLEntityRule.MULTIPLE)

	class TextInput(XMLEntityDef):
		description = XMLPrimitive('description', str, rule=XMLEntityRule.SINGLE)
		link = XMLPrimitive('link', str, rule=XMLEntityRule.SINGLE)
		name = XMLPrimitive('name', str, rule=XMLEntityRule.SINGLE)
		title = XMLPrimitive('title', str, rule=XMLEntityRule.SINGLE)

	description = XMLPrimitive('description', str, rule=XMLEntityRule.SINGLE)
	link = XMLPrimitive('link', str, rule=XMLEntityRule.SINGLE)
	title = XMLPrimitive('title', str, rule=XMLEntityRule.SINGLE)
	category = XMLEntity('category', Category, rule=XMLEntityRule.MULTIPLE_OPTIONAL)
	cloud = XMLEntity('cloud', Cloud, rule=XMLEntityRule.SINGLE_OPTIONAL)
	copyright = XMLPrimitive('copyright', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	docs = XMLPrimitive('docs', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	generator = XMLPrimitive('generator', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	image = XMLEntity('image', Image, rule=XMLEntityRule.SINGLE_OPTIONAL)
	language = XMLPrimitive('language', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	last_build_date = XMLPrimitive('lastBuildDate', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	managing_editor = XMLPrimitive('managingEditor', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	pub_date = XMLPrimitive('pubDate', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	rating = XMLPrimitive('rating', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
	skip_days = XMLEntity('skipDays', SkipDays, rule=XMLEntityRule.SINGLE_OPTIONAL)
	text_input = XMLEntity('textInput', TextInput, rule=XMLEntityRule.SINGLE_OPTIONAL)
	ttl = XMLPrimitive('ttl', int, rule=XMLEntityRule.SINGLE_OPTIONAL)
	web_master = XMLPrimitive('webMaster', str, rule=XMLEntityRule.SINGLE_OPTIONAL)

	items = XMLEntity('item', Item, rule=XMLEntityRule.MULTIPLE_OPTIONAL)

Channel.Empty = Channel(**{
	'description': '',
	'link': '',
	'title': '',
	'category': [],
	'cloud': None,
	'copyright': None,
	'docs': None,
	'generator': None,
	'image': None,
	'language': None,
	'last_build_date': None,
	'managing_editor': None,
	'pub_date': None,
	'rating': None,
	'skip_days': None,
	'text_input': None,
	'ttl': None,
	'web_master': None,

	'items': []
})

class RSSError(Exception):
	def __init__(self, message):
		super().__init__(message)

def parse_feed(source, strict=False):
	tree = ETree.fromstring(source)
	assert tree.tag == "rss", RSSError("Expected rss for root element, got '%s' instead" % tree.tag)
	assert tree.get('version') == '2.0', RSSError("Expected 2.0 for RSS version, got '%s' instead" % str(tree.get('version')))

	channel = tree.find('channel')
	assert channel is not None, RSSError("RSS element has no channel!")

	channel = Channel.from_xml(channel, strict)
	for item in channel.items:
		if item.description is None and item.title is None:
			raise RSSError("Item contains neither title nor description")

	return channel