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

import warnings
from ..util import parseBoolValue, WHEEL_MODE

class Extension:
    """ Base class for extensions to subclass. """

    # Default config -- to be overriden by a subclass
    # Must be of the following format:
    #     {
    #       'key': ['value', 'description']
    #     }
    # Note that Extension.setConfig will raise a KeyError
    # if a default is not set here.
    config = {}

    def __init__(self, **kwargs):
        """ Initiate Extension and set up configs. """
        self.setConfigs(kwargs)

    def getConfig(self, key, default=''):
        """ Return a setting for the given key or an empty string. """
        if key in self.config:
            return self.config[key][0]
        else:
            return default

    def getConfigs(self):
        """ Return all configs settings as a dict. """
        return {key: self.getConfig(key) for key in self.config.keys()}

    def getConfigInfo(self):
        """ Return all config descriptions as a list of tuples. """
        return [(key, self.config[key][1]) for key in self.config.keys()]

    def setConfig(self, key, value):
        """ Set a config setting for `key` with the given `value`. """
        if isinstance(self.config[key][0], bool):
            value = parseBoolValue(value)
        if self.config[key][0] is None:
            value = parseBoolValue(value, preserve_none=True)
        self.config[key][0] = value

    def setConfigs(self, items):
        """ Set multiple config settings given a dict or list of tuples. """
        if hasattr(items, 'items'):
            # it's a dict
            items = items.items()
        for key, value in items:
            self.setConfig(key, value)

    def _extendMarkdown(self, *args):
        """ Private wrapper around extendMarkdown. """
        md = args[0]
        try:
            self.extendMarkdown(md)
        except TypeError as e:
            if "missing 1 required positional argument" in str(e):
                # Must be a 2.x extension. Pass in a dumby md_globals.
                self.extendMarkdown(md, {})
                warnings.warn(
                    "The 'md_globals' parameter of '{}.{}.extendMarkdown' is "
                    "deprecated.".format(self.__class__.__module__, self.__class__.__name__),
                    category=DeprecationWarning,
                    stacklevel=2
                )
            else:
                raise

    def extendMarkdown(self, md):
        """
        Add the various proccesors and patterns to the Markdown Instance.

        This method must be overriden by every extension.

        Keyword arguments:

        * md: The Markdown instance.

        * md_globals: Global variables in the markdown module namespace.

        """
        raise NotImplementedError(
            'Extension "%s.%s" must define an "extendMarkdown"'
            'method.' % (self.__class__.__module__, self.__class__.__name__)
        )
