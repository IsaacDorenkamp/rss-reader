from __future__ import annotations

from datetime import datetime
import functools
from lxml.etree import XMLParser
from lxml.html import fromstring as html_fromstring
import typing

from .xml import *

from util import dateutil


class Category(XMLEntityDef):
    domain: typing.Optional[str] = XMLAttribute('domain')
    value: str = XMLTextContent(XMLTextContent.primitive)


class Cloud(XMLEntityDef):
    domain: typing.Optional[str] = XMLAttribute('domain')
    path: typing.Optional[str] = XMLAttribute('path')
    port: typing.Optional[str] = XMLAttribute('port')
    protocol: typing.Optional[str] = XMLAttribute('protocol')
    register_procedure: typing.Optional[str] = XMLAttribute('registerProcedure')


class Image(XMLEntityDef):
    link: str = XMLPrimitive('link', str, rule=XMLEntityRule.SINGLE)
    title: str = XMLPrimitive('title', str, rule=XMLEntityRule.SINGLE)
    url: str = XMLPrimitive('url', str, rule=XMLEntityRule.SINGLE)
    description: typing.Optional[str] = XMLPrimitive('description', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
    height: typing.Optional[int] = XMLPrimitive('height', int, rule=XMLEntityRule.SINGLE_OPTIONAL)
    width: typing.Optional[int] = XMLPrimitive('width', int, rule=XMLEntityRule.SINGLE_OPTIONAL)


class Item(XMLEntityDef):
    class Enclosure(XMLEntityDef):
        length: int = XMLAttribute('length', optional=False, processor=lambda x: int(x))
        type: str = XMLAttribute('type', optional=False)
        url: str = XMLAttribute('url', optional=False)

    class GUID(XMLEntityDef):
        is_permalink: typing.Optional[str] = XMLAttribute('isPermaLink')
        value: str = XMLTextContent(XMLTextContent.primitive)

    class Source(XMLEntityDef):
        url: str = XMLAttribute('url', optional=False)
        value: str = XMLTextContent(XMLTextContent.primitive)

    author: str = XMLPrimitive('author', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
    category: Category = XMLEntity('category', Category, rule=XMLEntityRule.MULTIPLE_OPTIONAL)
    comments: str = XMLPrimitive('comments', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
    description: str = XMLPrimitive('description', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
    enclosure: Enclosure = XMLEntity('enclosure', Enclosure, rule=XMLEntityRule.MULTIPLE_OPTIONAL)
    guid: GUID = XMLEntity('guid', GUID, rule=XMLEntityRule.SINGLE_OPTIONAL)
    link: str = XMLPrimitive('link', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
    pub_date: datetime = XMLPrimitive('pubDate', dateutil.parse, rule=XMLEntityRule.SINGLE_OPTIONAL)
    source: Source = XMLEntity('source', Source, rule=XMLEntityRule.SINGLE_OPTIONAL)
    title: str = XMLPrimitive('title', str, rule=XMLEntityRule.SINGLE_OPTIONAL)

    # These are our custom attributes which we use to track item state.
    read: bool = False

    @functools.cached_property
    def plain_description(self):
        return html_fromstring(self.description).text_content().strip()

    def __eq__(self, other: Item) -> bool:
        if self._parent and other._parent:
            channel = self._parent
            other_channel = other._parent
            if channel.link != other_channel.link:
                return False
        else:
            if self._parent or other._parent:
                return False

        if self.guid and other.guid:
            return self.guid.value == other.guid.value
        elif self.guid or other.guid:
            return False
        
        if self.link and other.link:
            return self.link == other.link
        elif self.link or other.link:
            return False

        if self.title and other.title:
            if self.description and other.description:
                return (self.description == other.description)\
                    and (self.title == other.title)
            elif self.description or other.description:
                return False
        elif self.title or other.title:
            return False
        
        return False

    def belongsTo(self, channel: Channel) -> bool:
        if self._parent:
            return self._parent == channel
        else:
            return False
    
    @property
    def channel(self) -> Channel:
        return self._parent


class Channel(XMLEntityDef):
    Empty: Channel
    Invalid: Channel

    class SkipDays(XMLEntityDef):
        days: typing.List[str] = XMLPrimitive('day', str, rule=XMLEntityRule.MULTIPLE)

    class SkipHours(XMLEntityDef):
        hours: typing.List[int] = XMLPrimitive('hour', int, rule=XMLEntityRule.MULTIPLE)

    class TextInput(XMLEntityDef):
        description: str = XMLPrimitive('description', str, rule=XMLEntityRule.SINGLE)
        link: str = XMLPrimitive('link', str, rule=XMLEntityRule.SINGLE)
        name: str = XMLPrimitive('name', str, rule=XMLEntityRule.SINGLE)
        title: str = XMLPrimitive('title', str, rule=XMLEntityRule.SINGLE)

    description: str = XMLPrimitive('description', str, rule=XMLEntityRule.SINGLE)
    link: str = XMLPrimitive('link', str, rule=XMLEntityRule.SINGLE)
    title: str = XMLPrimitive('title', str, rule=XMLEntityRule.SINGLE)
    category: typing.List[Category] = XMLEntity('category', Category, rule=XMLEntityRule.MULTIPLE_OPTIONAL)
    cloud: typing.Optional[Cloud] = XMLEntity('cloud', Cloud, rule=XMLEntityRule.SINGLE_OPTIONAL)
    copyright: typing.Optional[str] = XMLPrimitive('copyright', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
    docs: typing.Optional[str] = XMLPrimitive('docs', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
    generator: typing.Optional[str] = XMLPrimitive('generator', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
    image: typing.Optional[Image] = XMLEntity('image', Image, rule=XMLEntityRule.SINGLE_OPTIONAL)
    language: typing.Optional[str] = XMLPrimitive('language', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
    last_build_date: typing.Optional[str] = XMLPrimitive('lastBuildDate', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
    managing_editor: typing.Optional[str] = XMLPrimitive('managingEditor', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
    pub_date: datetime = XMLPrimitive('pubDate', dateutil.parse, rule=XMLEntityRule.SINGLE_OPTIONAL)
    rating: str = XMLPrimitive('rating', str, rule=XMLEntityRule.SINGLE_OPTIONAL)
    skip_days: typing.Optional[typing.List[str]] = XMLEntity('skipDays', SkipDays, rule=XMLEntityRule.SINGLE_OPTIONAL)
    skip_hours: typing.Optional[typing.List[int]] = XMLEntity('skipHours', SkipHours, rule=XMLEntityRule.SINGLE_OPTIONAL)
    text_input: typing.Optional[TextInput] = XMLEntity('textInput', TextInput, rule=XMLEntityRule.SINGLE_OPTIONAL)
    ttl: typing.Optional[int] = XMLPrimitive('ttl', int, rule=XMLEntityRule.SINGLE_OPTIONAL)
    web_master: typing.Optional[str] = XMLPrimitive('webMaster', str, rule=XMLEntityRule.SINGLE_OPTIONAL)

    items = XMLEntity('item', Item, rule=XMLEntityRule.MULTIPLE_OPTIONAL)

    ref: typing.Optional[str] = None
    """URL referring to this feed"""

    def __eq__(self, other: Channel) -> bool:
        if self.link and other.link:
            return self.link == other.link
        elif self.link or other.link:
            return False
        
        if self.ref and other.ref:
            return self.ref == other.ref
        elif self.ref or other.ref:
            return False
        
        return False


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

Channel.Invalid = Channel()


class RSSError(Exception):
    pass


def parse_feed(source: str, strict: bool = False) -> Channel:
    parser = XMLParser()
    parser.feed(clean_invalid_string(source))
    tree = parser.close()

    assert tree.tag == "rss", RSSError("Expected rss for root element, got '%s' instead" % tree.tag)
    assert tree.get('version') == '2.0', RSSError("Expected 2.0 for RSS version, got '%s' instead"
                                                  % str(tree.get('version')))

    channel = tree.find('channel')
    assert channel is not None, RSSError("RSS element has no channel!")

    channel = Channel.from_xml(channel, strict)
    for item in channel.items:
        if item.description is None and item.title is None:
            raise RSSError("Item contains neither title nor description")

    return channel
