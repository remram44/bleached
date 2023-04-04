import re


__all__ = ['UnsafeInput', 'check_html', 'is_html_bleached']


WHITESPACE = ' \t\n\r\v\f'

"""Those are tags that don't need a closing tag (and can't have one).

They can be seen with an slash at the end (ex: "<img/>") but that is not
required.

Other elements cannot use the ending slash syntax (ex: "<h1/>").
"""
VOID_ELEMENTS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta',
    'source', 'track', 'wbr',
}

ELEMENT_CHARS = (
    'abcdefghijklmnopqrstuvwxyz' +
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ' +
    '0123456789' +
    '-'
)
ELEMENT_CHARS = set(ELEMENT_CHARS)

ATTRIBUTE_CHARS = ELEMENT_CHARS

HTML_ENTITIES = {
    'nbsp': '\x20',
    'quot': '"',
    'amp': '&',
    'apos': "'",
    'lt': '<',
    'gt': '>',
}

DEFAULT_TAGS = {
    'p', 'br', 'code', 'blockquote', 'pre',  # formatting
    'sub', 'sup', 'caption',
    'a', 'img',  # non-text
    'h1', 'h2', 'h3', 'h4', 'h5',  # headers
    'strong', 'em', 'b', 'u', 'q', 'del',  # emphasis
    'ul', 'ol', 'li', 'dl', 'dt', 'dd',  # lists
    'table', 'thead', 'tbody', 'tr', 'th', 'td',  # tables
    'colgroup', 'col',  # columns
}

DEFAULT_ATTRIBUTES = {
    'a': {'href', 'title'},
    'img': {'src', 'width', 'height'},
}


class EndOfInput(ValueError):
    pass


class UnsafeInput(ValueError):
    def __init__(self, message, index, line, line_position):
        full_message = "Line %d character %d (input index %d): %s" % (
            line,
            line_position,
            index,
            message,
        )
        super(ValueError, self).__init__(full_message)
        self.message = message
        """Index in the string, 0-based."""
        self.index = index
        """Line number, 1-based."""
        self.line = line
        """Character number in the line, 1-based."""
        self.line_position = line_position


def check_html(
    source,
    *,
    tags=DEFAULT_TAGS,
    attributes=DEFAULT_ATTRIBUTES,
):
    Checker(source, tags=tags, attributes=attributes).check()


def is_html_bleached(
    source,
    *,
    tags=DEFAULT_TAGS,
    attributes=DEFAULT_ATTRIBUTES,
):
    try:
        check_html(source, tags=tags, attributes=attributes)
        return True
    except UnsafeInput:
        return False


class Checker(object):
    def __init__(self, source, *, tags, attributes):
        self.source = source
        self.tags = tags
        self.attributes = attributes
        self.position = 0
        self.line = 1
        self.line_position = 1
        self.element_stack = []

    def consume_char(self):
        c = self.peek_char()
        self.position += 1
        if c == '\n':
            self.line_position = 1
            self.line += 1
        else:
            self.line_position += 1
        return c

    def peek_char(self):
        if self.position >= len(self.source):
            raise EndOfInput
        return self.source[self.position:self.position + 1]

    def skip_whitespace(self):
        while self.peek_char() in WHITESPACE:
            self.consume_char()

    def check(self):
        try:
            while True:
                try:
                    c = self.peek_char()
                except EndOfInput:
                    break
                if c == '>':
                    self.fail("Unexpected '>' character")
                elif c == '<':
                    what, tag_name = self.read_tag()
                    if what == 'open':
                        if tag_name not in VOID_ELEMENTS:
                            self.element_stack.append(tag_name)
                            if len(self.element_stack) >= 1000:
                                self.fail("Element stack too deep")
                    elif what == 'close':
                        if self.element_stack and tag_name == self.element_stack[-1]:
                            self.element_stack.pop(-1)
                        else:
                            self.fail(
                                "Closing tag for wrong element %r" % tag_name,
                            )
                    else:
                        if tag_name not in VOID_ELEMENTS:
                            self.fail(
                                "Self-closing tag for non-void element %r" % (
                                    tag_name,
                                ),
                            )
                elif c == '&':
                    self.read_entity()
                else:
                    self.consume_char()
        except EndOfInput:
            self.fail("Unexpected end of input")

        if self.element_stack:
            self.fail(
                "Missing closing tag for element %r" % self.element_stack[-1],
            )

    def read_entity(self):
        """Reads an HTML entity, e.g. "&nbsp;".
        """
        assert self.consume_char() == '&'
        entity = []
        while True:
            c = self.consume_char()
            if c == ';':
                break
            elif len(entity) >= 10:
                self.fail("Entity too long")
            else:
                entity.append(c)
        entity = ''.join(entity).lower()
        if entity and entity[0] == '#':
            if not re.match('^#[0-9]+$', entity):
                self.fail("Invalid numerical entity")
        else:
            if entity not in HTML_ENTITIES:
                self.fail("Unknown HTML entity %r" % entity)
        return HTML_ENTITIES[entity]

    def read_tag(self):
        """Reads an HTML tag, e.g. either "<h1>" or "</h1>".

        This always assumes that tags are terminated, so "<br>" won't
        be accepted.
        """
        assert self.consume_char() == '<'
        self.skip_whitespace()
        if self.peek_char() == '/':
            closing = True
            self.consume_char()
            self.skip_whitespace()
        else:
            closing = False
        tag_name = []
        while True:
            c = self.peek_char()
            if c in WHITESPACE or c == '/' or c == '>':
                break
            elif c in ELEMENT_CHARS:
                tag_name.append(self.consume_char())
            else:
                self.fail("Unexpected character in tag name")

        tag_name = ''.join(tag_name).lower()
        if tag_name not in self.tags:
            self.fail("Found forbidden opening tag %r" % tag_name)

        if not closing:
            self.read_attributes(tag_name)

        self.skip_whitespace()
        c = self.consume_char()
        if c == '>':
            if closing:
                return 'close', tag_name
            else:
                return 'open', tag_name
        elif c == '/':
            if closing:
                self.fail("Saw tag with slashes on both sides")
            else:
                self.skip_whitespace()
                if self.consume_char() != '>':
                    self.fail("Missing tag close after ending slash")
                return 'selfclose', tag_name
        else:
            self.fail("Unexpected character in tag")

    def read_attributes(self, tag_name):
        """Reads the attributes of an HTML tag.
        """
        while True:
            self.skip_whitespace()

            if self.peek_char() in '>/':
                break

            # Read name
            attribute_name = []
            while True:
                c = self.peek_char()
                if c in WHITESPACE or c == '/' or c == '>' or c == '=':
                    break
                elif c in ATTRIBUTE_CHARS:
                    attribute_name.append(self.consume_char())
                else:
                    self.fail("Unexpected character in attribute")
            attribute_name = ''.join(attribute_name).lower()

            if attribute_name not in self.attributes.get(tag_name, ()):
                self.fail("Forbidden attribute %r in tag %r" % (
                    attribute_name,
                    tag_name,
                ))

            self.skip_whitespace()
            c = self.consume_char()
            if c != '=':
                self.fail("Unexpected character %r in attribute" % c)
            self.skip_whitespace()
            quote = self.consume_char()
            if quote != '"' and quote != "'":
                self.fail("Missing quote for attribute value")

            # Read value
            while True:
                c = self.peek_char()
                if c == quote:
                    self.consume_char()
                    break
                elif c in '<>':
                    self.fail("Forbidden character in attribute value")
                elif c == '&':
                    self.read_entity()
                else:
                    self.consume_char()

    def fail(self, message):
        raise UnsafeInput(
            message,
            self.position,
            self.line,
            self.line_position,
        )
