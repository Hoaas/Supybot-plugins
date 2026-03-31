###
# Copyright (c) 2010, Terje Hoås
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.test import *

from . import plugin as ddg_plugin


def makeXml(answer='', answertype='', abstract='', abstractsource='',
            abstracturl='', definition='', definitionsource='',
            results=(), topics=(), redirect=''):
    """Build a minimal DuckDuckGo Zero-Click XML response string."""
    result_xml = ''.join(
        f'<Results><Result><Text>{r["text"]}</Text>'
        f'<FirstURL>{r["url"]}</FirstURL></Result></Results>'
        for r in results
    )
    topic_xml = '<RelatedTopics>' + ''.join(
        f'<RelatedTopic><Text>{t["text"]}</Text>'
        f'<FirstURL>{t["url"]}</FirstURL></RelatedTopic>'
        for t in topics
    ) + '</RelatedTopics>'
    return (
        f'<DuckDuckGoResponse>'
        f'<Answer>{answer}</Answer>'
        f'<AnswerType>{answertype}</AnswerType>'
        f'<AbstractText>{abstract}</AbstractText>'
        f'<AbstractSource>{abstractsource}</AbstractSource>'
        f'<AbstractURL>{abstracturl}</AbstractURL>'
        f'<Definition>{definition}</Definition>'
        f'<DefinitionSource>{definitionsource}</DefinitionSource>'
        f'{result_xml}'
        f'{topic_xml}'
        f'<Redirect>{redirect}</Redirect>'
        f'</DuckDuckGoResponse>'
    ).encode()


# ---------------------------------------------------------------------------
# Unit tests for the parseResponse helper — no bot, no network
# ---------------------------------------------------------------------------

class ParseResponseTestCase(SupyTestCase):

    def testAnswerExtracted(self):
        xml = makeXml(answer='42', answertype='calc')
        data = ddg_plugin.parseResponse(xml)
        self.assertEqual(data['answer'], '42')
        self.assertEqual(data['answertype'], 'calc')

    def testAnswerWithoutTypeExtracted(self):
        xml = makeXml(answer='some answer')
        data = ddg_plugin.parseResponse(xml)
        self.assertEqual(data['answer'], 'some answer')
        self.assertEqual(data['answertype'], '')

    def testAbstractExtracted(self):
        xml = makeXml(abstract='Water is H2O.', abstractsource='Wikipedia',
                      abstracturl='https://en.wikipedia.org/wiki/Water')
        data = ddg_plugin.parseResponse(xml)
        self.assertEqual(data['abstract'], 'Water is H2O.')
        self.assertEqual(data['abstractsource'], 'Wikipedia')
        self.assertEqual(data['abstracturl'], 'https://en.wikipedia.org/wiki/Water')

    def testDefinitionExtracted(self):
        xml = makeXml(definition='H2O: a clear liquid.', definitionsource='Wiktionary')
        data = ddg_plugin.parseResponse(xml)
        self.assertEqual(data['definition'], 'H2O: a clear liquid.')
        self.assertEqual(data['definitionsource'], 'Wiktionary')

    def testResultsExtracted(self):
        xml = makeXml(results=[
            {'text': 'First result', 'url': 'https://example.com/1'},
            {'text': 'Second result', 'url': 'https://example.com/2'},
        ])
        data = ddg_plugin.parseResponse(xml)
        self.assertEqual(len(data['results']), 2)
        self.assertEqual(data['results'][0]['text'], 'First result')
        self.assertEqual(data['results'][0]['url'], 'https://example.com/1')
        self.assertEqual(data['results'][1]['text'], 'Second result')

    def testTopicsExtracted(self):
        xml = makeXml(topics=[
            {'text': 'Related topic A', 'url': 'https://example.com/a'},
        ])
        data = ddg_plugin.parseResponse(xml)
        self.assertEqual(len(data['topics']), 1)
        self.assertEqual(data['topics'][0]['text'], 'Related topic A')

    def testRedirectExtracted(self):
        xml = makeXml(redirect='https://duckduckgo.com/?q=something')
        data = ddg_plugin.parseResponse(xml)
        self.assertEqual(data['redirect'], 'https://duckduckgo.com/?q=something')

    def testAllEmptyFieldsReturnsDict(self):
        xml = makeXml()
        data = ddg_plugin.parseResponse(xml)
        self.assertIsNotNone(data)
        self.assertEqual(data['answer'], '')
        self.assertEqual(data['abstract'], '')
        self.assertEqual(data['definition'], '')
        self.assertEqual(data['results'], [])
        self.assertEqual(data['topics'], [])

    def testMalformedXmlReturnsNone(self):
        result = ddg_plugin.parseResponse(b'<not valid xml')
        self.assertIsNone(result)

    def testAcceptsBytesInput(self):
        xml = makeXml(answer='hello')
        self.assertIsInstance(xml, bytes)
        data = ddg_plugin.parseResponse(xml)
        self.assertEqual(data['answer'], 'hello')

    def testAcceptsStringInput(self):
        xml = makeXml(answer='hello').decode()
        self.assertIsInstance(xml, str)
        data = ddg_plugin.parseResponse(xml)
        self.assertEqual(data['answer'], 'hello')


# ---------------------------------------------------------------------------
# Integration tests for the bot command — network call is mocked
# ---------------------------------------------------------------------------

class DuckDuckGoCommandTestCase(PluginTestCase):
    plugins = ('DuckDuckGo',)

    def testCommandReturnsAnswer(self):
        xml = makeXml(answer='42', answertype='calc')
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: xml
        try:
            self.assertResponse('ddg 6 * 7', '42 (calc)')
        finally:
            utils.web.getUrl = original

    def testCommandReturnsAbstract(self):
        xml = makeXml(abstract='Water is a chemical compound.', abstractsource='Wikipedia')
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: xml
        try:
            self.assertResponse('ddg h2o', 'Water is a chemical compound. (Wikipedia)')
        finally:
            utils.web.getUrl = original

    def testCommandReturnsNoInfoMessage(self):
        xml = makeXml()
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: xml
        try:
            self.assertResponse('ddg xyzzy', 'No Zero-Click info from DuckDuckGo.')
        finally:
            utils.web.getUrl = original

    def testCommandReturnsNoInfoOnBadXml(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: b'<bad xml'
        try:
            self.assertResponse('ddg test', 'No Zero-Click info from DuckDuckGo.')
        finally:
            utils.web.getUrl = original
