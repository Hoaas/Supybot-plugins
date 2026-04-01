import supybot.utils as utils
from supybot.test import *

from . import plugin as wolfram_plugin


# ---------------------------------------------------------------------------
# XML fixture helpers
# ---------------------------------------------------------------------------

def _xml(body):
    """Wrap body in a minimal Wolfram queryresult envelope (success=true)."""
    return (
        '<?xml version="1.0"?>'
        f'<queryresult success="true" error="false">{body}</queryresult>'
    ).encode()


def _pod(title, text):
    return f'<pod title="{title}"><subpod><plaintext>{text}</plaintext></subpod></pod>'



def _noresult():
    return b'<?xml version="1.0"?><queryresult success="false" error="false"></queryresult>'


def _didyoumean(suggestion):
    return (
        '<?xml version="1.0"?>'
        f'<queryresult success="false" error="false">'
        f'<didyoumean>{suggestion}</didyoumean>'
        f'</queryresult>'
    ).encode()


def _apierror(msg):
    return (
        '<?xml version="1.0"?>'
        f'<queryresult success="false" error="true">'
        f'<error><msg>{msg}</msg></error>'
        f'</queryresult>'
    ).encode()


# ---------------------------------------------------------------------------
# Unit tests for module-level helpers
# ---------------------------------------------------------------------------

class WolframHelperTestCase(SupyTestCase):

    # formatPodText

    def testFormatPodTextPipe(self):
        self.assertEqual(
            wolfram_plugin.formatPodText('a | b | c'),
            'a: b: c',
        )

    def testFormatPodTextNewline(self):
        self.assertEqual(
            wolfram_plugin.formatPodText('a\nb\nc'),
            'a, b, c',
        )

    def testFormatPodTextBoth(self):
        self.assertEqual(
            wolfram_plugin.formatPodText('x | y\nz'),
            'x: y, z',
        )

    def testFormatPodTextNoChange(self):
        self.assertEqual(wolfram_plugin.formatPodText('hello'), 'hello')

    # parseWolframXml — error responses

    def testParseApiError(self):
        result = wolfram_plugin.parseWolframXml(_apierror('Invalid appid'))
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Invalid appid')

    def testParseDidYouMean(self):
        result = wolfram_plugin.parseWolframXml(_didyoumean('2 + 2'))
        self.assertIn('didyoumean', result)
        self.assertEqual(result['didyoumean'], ['2 + 2'])

    def testParseNoResults(self):
        result = wolfram_plugin.parseWolframXml(_noresult())
        self.assertIn('noresults', result)

    def testParseMalformedXml(self):
        result = wolfram_plugin.parseWolframXml(b'not xml at all')
        self.assertIn('error', result)

    # parseWolframXml — success responses

    def testParseSuccessSinglePod(self):
        xml = _xml(_pod('Result', '42'))
        result = wolfram_plugin.parseWolframXml(xml)
        self.assertIn('pods', result)
        self.assertEqual(result['pods'], [('Result', '42')])

    def testParseSuccessMultiplePods(self):
        xml = _xml(_pod('Result', '10') + _pod('Decimal form', '10.0'))
        result = wolfram_plugin.parseWolframXml(xml)
        self.assertEqual(result['pods'], [('Result', '10'), ('Decimal form', '10.0')])

    def testParseInputPodSkipped(self):
        xml = _xml(_pod('Input interpretation', '5 + 5') + _pod('Result', '10'))
        result = wolfram_plugin.parseWolframXml(xml)
        # 'Input interpretation' contains 'input' so it should be excluded.
        self.assertEqual(result['pods'], [('Result', '10')])

    def testParseInputPodCaseInsensitive(self):
        xml = _xml(_pod('INPUT', 'whatever') + _pod('Result', '42'))
        result = wolfram_plugin.parseWolframXml(xml)
        self.assertEqual(result['pods'], [('Result', '42')])

    def testParseEmptyPlaintextSkipped(self):
        # A pod with empty plaintext should not appear in pods.
        xml = (
            b'<?xml version="1.0"?>'
            b'<queryresult success="true" error="false">'
            b'<pod title="Result"><subpod><plaintext></plaintext></subpod></pod>'
            b'</queryresult>'
        )
        result = wolfram_plugin.parseWolframXml(xml)
        self.assertEqual(result['pods'], [])

    def testParseAcceptsBytesInput(self):
        xml = _xml(_pod('Result', '7'))
        self.assertIsInstance(xml, bytes)
        result = wolfram_plugin.parseWolframXml(xml)
        self.assertIn('pods', result)

    def testParsePodTextFormatted(self):
        xml = _xml(_pod('Result', 'a | b\nc'))
        result = wolfram_plugin.parseWolframXml(xml)
        self.assertEqual(result['pods'], [('Result', 'a: b, c')])


# ---------------------------------------------------------------------------
# Integration tests for the bot command
# ---------------------------------------------------------------------------

class WolframCommandTestCase(PluginTestCase):
    plugins = ('Wolfram',)
    config = {'supybot.plugins.Wolfram.apikey': 'testkey'}

    def testWolframResult(self):
        xml = _xml(_pod('Result', '10'))
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: xml
        try:
            self.assertResponse('wolfram 5+5', 'Result: 10')
        finally:
            utils.web.getUrl = original

    def testWolframSkipsInputPod(self):
        xml = _xml(_pod('Input interpretation', '5 + 5') + _pod('Result', '10'))
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: xml
        try:
            self.assertResponse('wolfram 5+5', 'Result: 10')
        finally:
            utils.web.getUrl = original

    def testWolframDefaultTwoPods(self):
        xml = _xml(
            _pod('Result', '10') +
            _pod('Decimal form', '10.0') +
            _pod('Number line', 'image only'),
        )
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: xml
        try:
            # Default maxoutput=2: only first two pods returned.
            self.assertResponse('wolfram 5+5', 'Result: 10')
        finally:
            utils.web.getUrl = original

    def testWolframLinesOption(self):
        xml = _xml(_pod('Result', '10') + _pod('Decimal form', '10.0'))
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: xml
        try:
            self.assertNotError('wolfram --lines 1 5+5')
        finally:
            utils.web.getUrl = original

    def testWolframNoResult(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: _noresult()
        try:
            self.assertError('wolfram unknowngarbage')
        finally:
            utils.web.getUrl = original

    def testWolframDidYouMean(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: _didyoumean('5 + 5')
        try:
            self.assertResponse('wolfram 5 ++ 5', 'Did you mean: 5 + 5?')
        finally:
            utils.web.getUrl = original

    def testWolframApiError(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: _apierror('Invalid appid')
        try:
            self.assertError('wolfram anything')
        finally:
            utils.web.getUrl = original

    def testWolframNetworkError(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: (_ for _ in ()).throw(IOError('network down'))
        try:
            self.assertError('wolfram anything')
        finally:
            utils.web.getUrl = original

    def testWolframNoApiKey(self):
        with conf.supybot.plugins.Wolfram.apikey.context(''):
            self.assertNotError('wolfram anything')
