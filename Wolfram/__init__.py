"""
Does stuff with Wolfram Alpha webservice.
"""

import supybot
import supybot.world as world

__version__ = ""
__author__ = supybot.Author(name='Ed Summers')
__contributors__ = {supybot.Author('Terje Hoås', 'Hoaas', 'terje@robogoat.dev'): []}
__url__ = ''

from . import config
from . import plugin
from importlib import reload
reload(config)
reload(plugin)

if world.testing:
    from . import test

Class = plugin.Class
configure = config.configure
