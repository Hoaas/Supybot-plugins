###
# Copyright (c) 2025, Terje Hoås
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

from supybot.test import *
import supybot.conf as conf
from unittest.mock import MagicMock, patch
import os
import tempfile

from . import plugin as mistral_plugin


# ---------------------------------------------------------------------------
# Minimal stubs for Mistral SDK response objects
# ---------------------------------------------------------------------------

class _ContentItem:
    def __init__(self, type_, text=None, url=None, title=None):
        self.type = type_
        self.text = text
        self.url = url
        self.title = title


class _Output:
    def __init__(self, type_, content=None):
        self.type = type_
        self.content = content


class _Response:
    def __init__(self, outputs=None):
        self.outputs = outputs or []


# ---------------------------------------------------------------------------
# Helper test cases (no bot, no network)
# ---------------------------------------------------------------------------

class MistralHelperTestCase(SupyTestCase):
    """Tests for module-level helper functions in plugin.py."""

    # --- load_prompt_template ---

    def testLoadPromptTemplateSmallChannel(self):
        text = mistral_plugin.load_prompt_template('small_channel')
        self.assertIsNotNone(text)
        self.assertGreater(len(text), 10)

    def testLoadPromptTemplateLargeChannel(self):
        text = mistral_plugin.load_prompt_template('large_channel')
        self.assertIsNotNone(text)
        self.assertGreater(len(text), 10)

    def testLoadPromptTemplateMissingReturnsNone(self):
        self.assertIsNone(mistral_plugin.load_prompt_template('nonexistent_template'))

    def testLoadPromptTemplateCustomFile(self):
        # Write a temporary template into the prompts dir and load it.
        prompts_dir = mistral_plugin._PROMPTS_DIR
        path = os.path.join(prompts_dir, '_test_custom.txt')
        try:
            with open(path, 'w') as f:
                f.write('  custom prompt content  ')
            text = mistral_plugin.load_prompt_template('_test_custom')
            self.assertEqual(text, 'custom prompt content')
        finally:
            if os.path.exists(path):
                os.remove(path)

    # --- extract_response_text ---

    def testExtractResponseTextStringContent(self):
        output = _Output('message.output', content="Hello IRC!")
        response = _Response([output])
        self.assertEqual(mistral_plugin.extract_response_text(response), "Hello IRC!")

    def testExtractResponseTextListContent(self):
        items = [_ContentItem('text', text="Part one "), _ContentItem('text', text="part two")]
        output = _Output('message.output', content=items)
        response = _Response([output])
        self.assertEqual(mistral_plugin.extract_response_text(response), "Part one part two")

    def testExtractResponseTextStripsWhitespace(self):
        output = _Output('message.output', content="  trimmed  ")
        response = _Response([output])
        self.assertEqual(mistral_plugin.extract_response_text(response), "trimmed")

    def testExtractResponseTextSkipsNonMessageOutput(self):
        output = _Output('tool_call', content="ignored")
        response = _Response([output])
        self.assertIsNone(mistral_plugin.extract_response_text(response))

    def testExtractResponseTextNoOutputs(self):
        response = _Response([])
        self.assertIsNone(mistral_plugin.extract_response_text(response))

    def testExtractResponseTextMixedListSkipsNonText(self):
        items = [
            _ContentItem('tool_reference', url="https://example.com"),
            _ContentItem('text', text="actual answer"),
        ]
        output = _Output('message.output', content=items)
        response = _Response([output])
        self.assertEqual(mistral_plugin.extract_response_text(response), "actual answer")

    # --- extract_sources ---

    def testExtractSourcesFindsUrls(self):
        items = [
            _ContentItem('tool_reference', url="https://example.com", title="Example"),
            _ContentItem('tool_reference', url="https://other.org", title="Other"),
        ]
        output = _Output('message.output', content=items)
        response = _Response([output])
        sources = mistral_plugin.extract_sources(response)
        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0]['url'], "https://example.com")
        self.assertEqual(sources[0]['title'], "Example")
        self.assertEqual(sources[1]['url'], "https://other.org")

    def testExtractSourcesSkipsItemsWithoutUrl(self):
        items = [
            _ContentItem('tool_reference', url="", title="No URL"),
            _ContentItem('tool_reference', url="https://good.com", title="Good"),
        ]
        output = _Output('message.output', content=items)
        response = _Response([output])
        sources = mistral_plugin.extract_sources(response)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]['url'], "https://good.com")

    def testExtractSourcesEmptyResponse(self):
        response = _Response([])
        self.assertEqual(mistral_plugin.extract_sources(response), [])

    def testExtractSourcesSkipsNonMessageOutputs(self):
        items = [_ContentItem('tool_reference', url="https://example.com")]
        output = _Output('other_type', content=items)
        response = _Response([output])
        self.assertEqual(mistral_plugin.extract_sources(response), [])

    # --- get_last_messages ---

    def testGetLastMessagesFiltersChannel(self):
        class FakeMsg:
            def __init__(self, channel, nick, text, command='PRIVMSG'):
                self.channel = channel
                self.nick = nick
                self.args = ['', text]
                self.command = command

        history = [
            FakeMsg('#other', 'alice', 'not this'),
            FakeMsg('#test', 'bob', 'hello'),
            FakeMsg('#test', 'carol', 'world'),  # most recent (first after reverse)
        ]
        # reversed(history) = [carol/world, bob/hello, alice/not this]
        # [1:2] skips carol (triggering msg), takes bob
        result = mistral_plugin.get_last_messages(history, '#test', 2)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 'bob')
        self.assertEqual(result[0][1], 'hello')

    def testGetLastMessagesSkipsNonPrivmsg(self):
        class FakeMsg:
            def __init__(self, channel, nick, text, command='PRIVMSG'):
                self.channel = channel
                self.nick = nick
                self.args = ['', text]
                self.command = command

        history = [
            FakeMsg('#test', 'bot', 'join notice', command='JOIN'),
            FakeMsg('#test', 'alice', 'hi'),
            FakeMsg('#test', 'bob', 'trigger'),  # most recent
        ]
        result = mistral_plugin.get_last_messages(history, '#test', 5)
        # reversed: bob(skip), alice -> result should be just alice
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 'alice')

    def testGetLastMessagesEmptyHistory(self):
        result = mistral_plugin.get_last_messages([], '#test', 5)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# Command test cases
# ---------------------------------------------------------------------------

class MistralCommandTestCase(PluginTestCase):
    """Tests for bot commands."""
    plugins = ('Mistral',)
    config = {
        'supybot.plugins.Mistral.apiKey': 'test-fake-key',
        'supybot.plugins.Mistral.enableWebSearch': 'False',
    }

    def testMistralCommandDocstring(self):
        self.assertHelp('mistral')

    def testMistralreloadCommandDocstring(self):
        # mistralreload returns an error (no client) before showing help,
        # so verify it's registered by checking the error rather than help text.
        self.assertError('mistralreload')

    def testMistrallangCommandDocstring(self):
        # mistrallang requires a channel context — tested in MistralChannelCommandTestCase
        pass

    def testMistralCommandReturnsErrorWithoutWorkingClient(self):
        self.assertError('mistral hello world')

    def testMistralCommandReturnsResponseWhenClientWorks(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = 'Hello from Mistral!'

        with patch('Mistral.plugin.MistralClient') as MockClient:
            MockClient.return_value.chat.complete.return_value = mock_response
            cb = self.irc.getCallback('Mistral')
            cb.client = MockClient.return_value
            cb.agent = None
            with conf.supybot.plugins.Mistral.enableWebSearch.context(False):
                self.assertResponse('mistral hello', 'Hello from Mistral!')

    def testMistralCommandTruncatesLongResponse(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = 'x' * 500

        with patch('Mistral.plugin.MistralClient') as MockClient:
            MockClient.return_value.chat.complete.return_value = mock_response
            cb = self.irc.getCallback('Mistral')
            cb.client = MockClient.return_value
            cb.agent = None
            with conf.supybot.plugins.Mistral.enableWebSearch.context(False):
                msg = self.getMsg('mistral hello')
                reply = msg.args[1]
                self.assertLessEqual(len(reply), 403)  # maxResponseLength(400) + "..."
                self.assertTrue(reply.endswith('...'))


class MistralChannelCommandTestCase(ChannelPluginTestCase):
    """Tests for channel-context commands (mistrallang)."""
    plugins = ('Mistral',)
    config = {
        'supybot.plugins.Mistral.apiKey': 'test-fake-key',
        'supybot.plugins.Mistral.enableWebSearch': 'False',
    }

    def testMistrallangCommandDocstring(self):
        self.assertRegexp('help mistrallang', 'language')

    def testMistrallangShowsAutoDetectWhenEmpty(self):
        self.assertRegexp('mistrallang', 'auto-detect')

    def testMistrallangSetsAndShowsLanguage(self):
        self.assertRegexp('mistrallang no', "set to 'no'")
        self.assertRegexp('mistrallang', "set to 'no'")
        self.assertRegexp('mistrallang off', 'auto-detect')

