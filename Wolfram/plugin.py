import urllib.parse
from xml.etree import ElementTree

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.callbacks as callbacks
import supybot.ircutils as ircutils

try:
    from supybot.i18n import PluginInternationalization, internationalizeDocstring
    _ = PluginInternationalization('Wolfram')
except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f


_WOLFRAM_URL = 'https://api.wolframalpha.com/v2/query?'
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
}


def formatPodText(text):
    """Clean up a Wolfram pod plaintext value for IRC display.

    Replaces ' | ' with ': ' and newlines with ', '.
    """
    text = text.replace(' | ', ': ')
    text = text.replace('\n', ', ')
    return text


def parseWolframXml(xml):
    """Parse a Wolfram Alpha v2 XML response.

    Returns one of:
      {'error': str}           — API-level error message
      {'didyoumean': [str]}    — no results but suggestions exist
      {'noresults': True}      — no results and no suggestions
      {'pods': [(title, text), ...]}  — list of (title, plaintext) for all
                                        pods that have plaintext, excluding
                                        any pod whose title contains 'input'
                                        (case-insensitive).
    """
    if isinstance(xml, bytes):
        xml = xml.decode('utf-8', 'ignore')
    try:
        tree = ElementTree.fromstring(xml)
    except ElementTree.ParseError as e:
        return {'error': str(e)}

    if tree.attrib.get('success') == 'false':
        for results in tree.findall('.//error'):
            for err in results.findall('.//msg'):
                if err.text:
                    return {'error': err.text}
        dyms = [d.text for d in tree.findall('.//didyoumean') if d.text]
        if dyms:
            return {'didyoumean': dyms}
        return {'noresults': True}

    pods = []
    for pod in tree.findall('.//pod'):
        title = pod.attrib.get('title', '')
        if 'input' in title.lower():
            continue
        for plaintext in pod.findall('.//plaintext'):
            if plaintext.text:
                pods.append((title, formatPodText(plaintext.text)))
                break  # one plaintext per pod
    return {'pods': pods}


class Wolfram(callbacks.Plugin):
    """Plugin for querying the Wolfram Alpha API."""
    threaded = True

    @wrap([getopts({'lines': 'positiveInt'}), 'text'])
    @internationalizeDocstring
    def wolfram(self, irc, msg, args, options, question):
        """[--lines <num>] <query>

        Ask Wolfram Alpha a question. Uses the Wolfram Alpha API.
        --lines sets the maximum number of results to return (default 2).
        """
        apikey = self.registryValue('apikey')
        if not apikey or apikey == 'Not set':
            irc.reply(_("API key not set. See 'config help supybot.plugins.Wolfram.apikey'."))
            return

        maxoutput = dict(options).get('lines', 2)

        url = _WOLFRAM_URL + urllib.parse.urlencode({'input': question, 'appid': apikey})
        try:
            xml = utils.web.getUrl(url, headers=_HEADERS)
        except Exception as e:
            self.log.warning('Wolfram Alpha request failed: %s', e)
            irc.error(_('Failed to contact Wolfram Alpha.'))
            return

        result = parseWolframXml(xml)

        if 'error' in result:
            irc.error(_('Error: %s') % result['error'])
        elif 'didyoumean' in result:
            for suggestion in result['didyoumean']:
                irc.reply(_('Did you mean: %s?') % suggestion)
        elif 'noresults' in result:
            irc.error(_('No results found.'))
        else:
            pods = result['pods']
            if not pods:
                irc.error(_('No results found.'))
                return
            for title, text in pods[:maxoutput]:
                irc.reply(f'{title}: {text}')


Class = Wolfram
