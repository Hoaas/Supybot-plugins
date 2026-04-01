import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Wolfram')
except ImportError:
    _ = lambda x: x


def configure(advanced):
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Wolfram', True)


Wolfram = conf.registerPlugin('Wolfram')
conf.registerGlobalValue(Wolfram, 'apikey', registry.String('Not set', """API key to use WolframAlpha API. A key can be requested at https://developer.wolframalpha.com/.""", private=True))
