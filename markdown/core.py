"""
Python Markdown

A Python implementation of John Gruber's Markdown.

Documentation: https://python-markdown.github.io/
GitHub: https://github.com/Python-Markdown/markdown/
PyPI: https://pypi.org/project/Markdown/

Started by Manfred Stienstra (http://www.dwerg.net/).
Maintained for a few years by Yuri Takhteyev (http://www.freewisdom.org).
Currently maintained by Waylan Limberg (https://github.com/waylan),
Dmitry Shachnev (https://github.com/mitya57) and Isaac Muse (https://github.com/facelessuser).

Copyright 2007-2018 The Python Markdown Project (v. 1.7 and later)
Copyright 2004, 2005, 2006 Yuri Takhteyev (v. 0.2-1.6b)
Copyright 2004 Manfred Stienstra (the original version)

License: BSD (see LICENSE.md for details).
"""

import codecs
import sys
import logging
import importlib
from . import util
from .preprocessors import build_preprocessors
from .blockprocessors import build_block_parser
from .treeprocessors import build_treeprocessors
from .inlinepatterns import build_inlinepatterns
from .postprocessors import build_postprocessors
from .extensions import Extension
from .serializers import to_html_string, to_xhtml_string

__all__ = ['Markdown', 'markdown', 'markdownFromFile']


logger = logging.getLogger('MARKDOWN')


class Markdown:
    """Convert Markdown to HTML."""

    doc_tag = "div"     # Element used to wrap document - later removed

    output_formats = {
        'html':   to_html_string,
        'xhtml':  to_xhtml_string,
    }

    def __init__(self, **kwargs):
        """
        Creates a new Markdown instance.

        Keyword arguments:

        * extensions: A list of extensions.
            If an item is an instance of a subclass of `markdown.extension.Extension`, the  instance will be used
            as-is. If an item is of type string, first an entry point will be loaded. If that fails, the string is
            assumed to use Python dot notation (`path.to.module:ClassName`) to load a markdown.Extension subclass. If
            no class is specified, then a `makeExtension` function is called within the specified module.
        * extension_configs: Configuration settings for extensions.
        * output_format: Format of output. Supported formats are:
            * "xhtml": Outputs XHTML style tags. Default.
            * "html": Outputs HTML style tags.
        * tab_length: Length of tabs in the source. Default: 4

        """

        self.tab_length = kwargs.get('tab_length', 4)

        self.path = kwargs.get('path', './')
        self.lib_py = ''
        self.lib_cpp = ''
        self.lib_matlab = ''
        self.json_data = ''
        self.json_sym = ''
        self.changed_dict = {}  # whether the code block in certain context has been changed
        self.figure_list = []
        self.need_gen_figure = False
        self.parser_type = kwargs.get('parser_type', 4)
        self.bibtex_file = kwargs.get('bibtex_file', '')
        self.order = kwargs.get('order', 'unsorted')
        self.ESCAPED_CHARS = ['\\', '`', '*', '_', '{', '}', '[', ']',
                              '(', ')', '>', '#', '+', '-', '.', '!']

        self.block_level_elements = [
            # Elements which are invalid to wrap in a `<p>` tag.
            # See https://w3c.github.io/html/grouping-content.html#the-p-element
            'address', 'article', 'aside', 'blockquote', 'details', 'div', 'dl',
            'fieldset', 'figcaption', 'figure', 'footer', 'form', 'h1', 'h2', 'h3',
            'h4', 'h5', 'h6', 'header', 'hgroup', 'hr', 'main', 'menu', 'nav', 'ol',
            'p', 'pre', 'section', 'table', 'ul',
            # Other elements which Markdown should not be mucking up the contents of.
            'canvas', 'colgroup', 'dd', 'body', 'dt', 'group', 'iframe', 'li', 'legend',
            'math', 'map', 'noscript', 'output', 'object', 'option', 'progress', 'script',
            'style', 'tbody', 'td', 'textarea', 'tfoot', 'th', 'thead', 'tr', 'video'
        ]

        self.registeredExtensions = []
        self.docType = ""
        self.stripTopLevelTags = True

        self.build_parser()

        self.references = {}
        self.htmlStash = util.HtmlStash()
        self.registerExtensions(extensions=kwargs.get('extensions', []),
                                configs=kwargs.get('extension_configs', {}))
        self.set_output_format(kwargs.get('output_format', 'xhtml'))
        self.reset()

    def build_parser(self):
        """ Build the parser from the various parts. """
        self.preprocessors = build_preprocessors(self)
        self.parser = build_block_parser(self)
        self.inlinePatterns = build_inlinepatterns(self)
        self.treeprocessors = build_treeprocessors(self)
        self.postprocessors = build_postprocessors(self)
        return self

    def registerExtensions(self, extensions, configs):
        """
        Register extensions with this instance of Markdown.

        Keyword arguments:

        * extensions: A list of extensions, which can either
           be strings or objects.
        * configs: A dictionary mapping extension names to config options.

        """
        for ext in extensions:
            if isinstance(ext, str):
                ext = self.build_extension(ext, configs.get(ext, {}))
            if isinstance(ext, Extension):
                ext._extendMarkdown(self)
                logger.debug(
                    'Successfully loaded extension "%s.%s".'
                    % (ext.__class__.__module__, ext.__class__.__name__)
                )
            elif ext is not None:
                raise TypeError(
                    'Extension "{}.{}" must be of type: "{}.{}"'.format(
                        ext.__class__.__module__, ext.__class__.__name__,
                        Extension.__module__, Extension.__name__
                    )
                )
        return self

    def build_extension(self, ext_name, configs):
        """
        Build extension from a string name, then return an instance.

        First attempt to load an entry point. The string name must be registered as an entry point in the
        `markdown.extensions` group which points to a subclass of the `markdown.extensions.Extension` class.
        If multiple distributions have registered the same name, the first one found is returned.

        If no entry point is found, assume dot notation (`path.to.module:ClassName`). Load the specified class and
        return an instance. If no class is specified, import the module and call a `makeExtension` function and return
        the Extension instance returned by that function.
        """
        configs = dict(configs)

        entry_points = [ep for ep in util.INSTALLED_EXTENSIONS if ep.name == ext_name]
        if entry_points:
            ext = entry_points[0].load()
            return ext(**configs)

        # Get class name (if provided): `path.to.module:ClassName`
        ext_name, class_name = ext_name.split(':', 1) if ':' in ext_name else (ext_name, '')

        try:
            module = importlib.import_module(ext_name)
            logger.debug(
                'Successfully imported extension module "%s".' % ext_name
            )
        except ImportError as e:
            message = 'Failed loading extension "%s".' % ext_name
            e.args = (message,) + e.args[1:]
            raise

        if class_name:
            # Load given class name from module.
            return getattr(module, class_name)(**configs)
        else:
            # Expect  makeExtension() function to return a class.
            try:
                return module.makeExtension(**configs)
            except AttributeError as e:
                message = e.args[0]
                message = "Failed to initiate extension " \
                          "'%s': %s" % (ext_name, message)
                e.args = (message,) + e.args[1:]
                raise

    def registerExtension(self, extension):
        """ This gets called by the extension """
        self.registeredExtensions.append(extension)
        return self

    def reset(self):
        """
        Resets all state variables so that we can start with a new text.
        """
        self.htmlStash.reset()
        self.references.clear()

        for extension in self.registeredExtensions:
            if hasattr(extension, 'reset'):
                extension.reset()

        return self

    def set_output_format(self, format):
        """ Set the output format for the class instance. """
        self.output_format = format.lower().rstrip('145')  # ignore num
        try:
            self.serializer = self.output_formats[self.output_format]
        except KeyError as e:
            valid_formats = list(self.output_formats.keys())
            valid_formats.sort()
            message = 'Invalid Output Format: "%s". Use one of %s.' \
                % (self.output_format,
                   '"' + '", "'.join(valid_formats) + '"')
            e.args = (message,) + e.args[1:]
            raise
        return self

    def is_block_level(self, tag):
        """Check if the tag is a block level HTML tag."""
        if isinstance(tag, str):
            return tag.lower().rstrip('/') in self.block_level_elements
        # Some ElementTree tags are not strings, so return False.
        return False

    def convert(self, source):
        """
        Convert markdown to serialized XHTML or HTML.

        Keyword arguments:

        * source: Source text as a Unicode string.

        Markdown processing takes place in five steps:

        1. A bunch of "preprocessors" munge the input text.
        2. BlockParser() parses the high-level structural elements of the
           pre-processed text into an ElementTree.
        3. A bunch of "treeprocessors" are run against the ElementTree. One
           such treeprocessor runs InlinePatterns against the ElementTree,
           detecting inline markup.
        4. Some post-processors are run against the text after the ElementTree
           has been serialized into text.
        5. The output is written to a string.

        """

        # Fixup the source text
        if not source.strip():
            return ''  # a blank unicode string

        try:
            source = str(source)
        except UnicodeDecodeError as e:  # pragma: no cover
            # Customise error message while maintaining original trackback
            e.reason += '. -- Note: Markdown only accepts unicode input!'
            raise

        # Split into lines and run the line preprocessors.
        self.lines = source.split("\n")
        for prep in self.preprocessors:
            self.lines = prep.run(self.lines, path=self.path)

        # Parse the high-level elements.
        root = self.parser.parseDocument(self.lines).getroot()

        # Run the tree-processors
        for treeprocessor in self.treeprocessors:
            newRoot = treeprocessor.run(root)
            if newRoot is not None:
                root = newRoot

        # Serialize _properly_.  Strip top-level tags.
        output = self.serializer(root)
        if self.stripTopLevelTags:
            try:
                start = output.index(
                    '<%s>' % self.doc_tag) + len(self.doc_tag) + 2
                end = output.rindex('</%s>' % self.doc_tag)
                output = output[start:end].strip()
            except ValueError as e:  # pragma: no cover
                if output.strip().endswith('<%s />' % self.doc_tag):
                    # We have an empty document
                    output = ''
                else:
                    # We have a serious problem
                    raise ValueError('Markdown failed to strip top-level '
                                     'tags. Document=%r' % output.strip()) from e

        # Run the text post-processors
        for pp in self.postprocessors:
            output = pp.run(output)

        return output.strip()

    def convertFile(self, input=None, output=None, encoding=None):
        """Converts a markdown file and returns the HTML as a unicode string.

        Decodes the file using the provided encoding (defaults to utf-8),
        passes the file content to markdown, and outputs the html to either
        the provided stream or the file with provided name, using the same
        encoding as the source file. The 'xmlcharrefreplace' error handler is
        used when encoding the output.

        **Note:** This is the only place that decoding and encoding of unicode
        takes place in Python-Markdown.  (All other code is unicode-in /
        unicode-out.)

        Keyword arguments:

        * input: File object or path. Reads from stdin if `None`.
        * output: File object or path. Writes to stdout if `None`.
        * encoding: Encoding of input and output files. Defaults to utf-8.

        """

        encoding = encoding or "utf-8"

        # Read the source
        if input:
            if isinstance(input, str):
                input_file = codecs.open(input, mode="r", encoding=encoding)
            else:
                input_file = codecs.getreader(encoding)(input)
            text = input_file.read()
            input_file.close()
        else:
            text = sys.stdin.read()
            if not isinstance(text, str):  # pragma: no cover
                text = text.decode(encoding)

        text = text.lstrip('\ufeff')  # remove the byte-order mark

        # Convert
        html = self.convert(text)

        # Write to file or stdout
        if output:
            if isinstance(output, str):
                output_file = codecs.open(output, "w",
                                          encoding=encoding,
                                          errors="xmlcharrefreplace")
                output_file.write(html)
                output_file.close()
            else:
                writer = codecs.getwriter(encoding)
                output_file = writer(output, errors="xmlcharrefreplace")
                output_file.write(html)
                # Don't close here. User may want to write more.
        else:
            # Encode manually and write bytes to stdout.
            html = html.encode(encoding, "xmlcharrefreplace")
            try:
                # Write bytes directly to buffer (Python 3).
                sys.stdout.buffer.write(html)
            except AttributeError:  # pragma: no cover
                # Probably Python 2, which works with bytes by default.
                sys.stdout.write(html)

        return self


"""
EXPORTED FUNCTIONS
=============================================================================

Those are the two functions we really mean to export: markdown() and
markdownFromFile().
"""


def markdown(text, **kwargs):
    """Convert a markdown string to HTML and return HTML as a unicode string.

    This is a shortcut function for `Markdown` class to cover the most
    basic use case.  It initializes an instance of Markdown, loads the
    necessary extensions and runs the parser on the given text.

    Keyword arguments:

    * text: Markdown formatted text as Unicode or ASCII string.
    * Any arguments accepted by the Markdown class.

    Returns: An HTML document as a string.

    """
    md = Markdown(**kwargs)
    return md.convert(text)


def markdownFromFile(**kwargs):
    """Read markdown code from a file and write it to a file or a stream.

    This is a shortcut function which initializes an instance of Markdown,
    and calls the convertFile method rather than convert.

    Keyword arguments:

    * input: a file name or readable object.
    * output: a file name or writable object.
    * encoding: Encoding of input and output.
    * Any arguments accepted by the Markdown class.

    """
    md = Markdown(**kwargs)
    md.convertFile(kwargs.get('input', None),
                   kwargs.get('output', None),
                   kwargs.get('encoding', None))
