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
import urllib.parse
import xml.etree.ElementTree as etree

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization, internationalizeDocstring
    _ = PluginInternationalization('DuckDuckGo')
except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f


def parseResponse(xml_bytes):
    """Parse a DuckDuckGo Zero-Click API XML response.

    Returns a dict with keys:
        answer, answertype, abstract, abstractsource, abstracturl,
        definition, definitionsource, results, topics, redirect

    results and topics are lists of dicts with keys 'text' and 'url'.
    Returns None if the XML cannot be parsed.
    """
    if isinstance(xml_bytes, bytes):
        xml_bytes = xml_bytes.decode()
    try:
        root = etree.fromstring(xml_bytes)
    except etree.ParseError:
        return None

    results = [
        {'text': r.findtext('Text') or '', 'url': r.findtext('FirstURL') or ''}
        for r in root.findall('Results/Result')
    ]
    topics = [
        {'text': t.findtext('Text') or '', 'url': t.findtext('FirstURL') or ''}
        for t in root.findall('RelatedTopics/RelatedTopic')
        if t.findtext('Text')
    ] + [
        {'text': t.findtext('Text') or '', 'url': t.findtext('FirstURL') or ''}
        for t in root.findall('RelatedTopics/RelatedTopicsSection/RelatedTopic')
        if t.findtext('Text')
    ]

    return {
        'answer':           root.findtext('Answer'),
        'answertype':       root.findtext('AnswerType'),
        'abstract':         root.findtext('AbstractText'),
        'abstractsource':   root.findtext('AbstractSource'),
        'abstracturl':      root.findtext('AbstractURL'),
        'definition':       root.findtext('Definition'),
        'definitionsource': root.findtext('DefinitionSource'),
        'results':          results,
        'topics':           topics,
        'redirect':         root.findtext('Redirect'),
    }


class DuckDuckGo(callbacks.Plugin):
    """Uses the DuckDuckGo Zero-Click Info API to return instant answers,
    abstracts, definitions and related results for a query."""
    threaded = True

    @wrap(['text'])
    @internationalizeDocstring
    def ddg(self, irc, msg, args, query):
        """<query>

        Searches DuckDuckGo and returns any Zero-Click information available."""
        maxreplies = 3
        url = (
            'https://api.duckduckgo.com/?format=xml&no_html=1&no_redirect=1&kp=-1&q='
            + urllib.parse.quote(query)
        )
        xml = utils.web.getUrl(url)
        data = parseResponse(xml)
        if data is None:
            self.log.warning('DuckDuckGo: failed to parse XML response for query %s', query)
            irc.reply(_('No Zero-Click info from DuckDuckGo.'))
            return

        repliessofar = 0

        answer = data['answer']
        if answer and repliessofar < maxreplies:
            answertype = data['answertype']
            if answertype:
                irc.reply(f'{answer.strip()} ({answertype})')
            else:
                irc.reply(answer.strip())
            repliessofar += 1

        abstract = data['abstract']
        if abstract and repliessofar < maxreplies:
            asrc = f' ({data["abstractsource"]})' if data['abstractsource'] else ''
            irc.reply(abstract.strip() + asrc)
            repliessofar += 1
            return

        definition = data['definition']
        if definition and repliessofar < maxreplies:
            dsrc = f' ({data["definitionsource"]})' if data['definitionsource'] else ''
            irc.reply(definition.strip() + dsrc)
            repliessofar += 1
            return

        for result in data['results']:
            if repliessofar >= maxreplies:
                break
            irc.reply(result['text'].strip())
            repliessofar += 1

        for topic in data['topics']:
            if repliessofar >= maxreplies:
                break
            irc.reply(topic['text'].strip())
            repliessofar += 1

        redirect = data['redirect']
        if redirect and repliessofar < maxreplies:
            irc.reply(redirect)
            repliessofar += 1

        if repliessofar == 0:
            irc.reply(_('No Zero-Click info from DuckDuckGo.'))


Class = DuckDuckGo
