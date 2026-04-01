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

from supybot import conf, registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Mistral')
except ImportError:
    _ = lambda x: x


def configure(advanced):
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Mistral', True)


Mistral = conf.registerPlugin('Mistral')

conf.registerGlobalValue(Mistral, 'apiKey',
    registry.String('', _("""Your Mistral API key. You can get one from
    https://console.mistral.ai/. This is required for the plugin to work."""),
    private=True))

conf.registerGlobalValue(Mistral, 'model',
    registry.String('mistral-medium-2505', _("""The Mistral model to use.
    Default is mistral-medium-2505.""")))

conf.registerGlobalValue(Mistral, 'temperature',
    registry.Float(0.7, _("""Temperature for response generation.
    Lower values make responses more focused and deterministic.""")))

conf.registerGlobalValue(Mistral, 'maxResponseLength',
    registry.PositiveInteger(400, _("""Maximum length of responses in characters.
    Responses longer than this will be truncated for IRC compatibility.""")))

conf.registerGlobalValue(Mistral, 'contextHistory',
    registry.PositiveInteger(10, _("""Number of recent chat messages to include
    as context when making requests to Mistral.""")))

conf.registerGlobalValue(Mistral, 'enableWebSearch',
    registry.Boolean(True, _("""Whether to enable web search capabilities.
    When enabled, Mistral can search the web for current information.""")))

conf.registerGlobalValue(Mistral, 'agentId',
    registry.String('', _("""Mistral Agent ID to use for websearch. Set automatically
    after the first successful agent create or lookup. You can also set this manually
    to pin a specific agent. Example: ag_<agent_id>""")))

conf.registerGlobalValue(Mistral, 'promptTemplate',
    registry.String('small_channel', _("""Name of the prompt template file to use as
    the agent's system instructions. Templates are stored as .txt files in the plugin's
    prompts/ directory. Bundled templates: small_channel, large_channel.
    Change takes effect after 'mistralreload'.""")))
