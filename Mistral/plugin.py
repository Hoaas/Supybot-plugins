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

import os
import re

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Mistral')
except ImportError:
    _ = lambda x: x

from mistralai.client import Mistral as MistralClient

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'prompts')


def load_prompt_template(name):
    """Load a prompt template by name from the prompts/ directory.

    Returns the template text, or None if the file is not found.
    The *name* should not include the .txt extension.
    """
    path = os.path.join(_PROMPTS_DIR, f'{name}.txt')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except OSError:
        return None


def get_last_messages(history, channel, limit):
    """Return the last *limit* (nick, text) pairs from *history* for *channel*.

    *history* is an iterable of IrcMsg objects (e.g. irc.state.history).
    The most-recent message (index 0 in reversed order) is skipped because it
    is the command that triggered this call.
    """
    messages_in_channel = filter(
        lambda x: x.channel == channel and x.command == 'PRIVMSG',
        reversed(history)
    )
    # Skip the triggering message (first item), take up to *limit* more.
    selected = reversed(list(messages_in_channel)[1:limit])
    return [
        (m.nick, ircutils.stripFormatting(m.args[1]))
        for m in selected
    ]


def extract_response_text(response):
    """Extract the main text from a Mistral conversation response object.

    Returns the concatenated text string, or None if nothing could be found.
    Note: this function does not log errors; callers should handle None.
    """
    if not (hasattr(response, 'outputs') and response.outputs):
        return None
    for output in response.outputs:
        if not (hasattr(output, 'type') and output.type == 'message.output'):
            continue
        if not (hasattr(output, 'content') and output.content):
            continue
        content = output.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if hasattr(item, 'type') and item.type == 'text' and hasattr(item, 'text'):
                    text_parts.append(item.text)
                elif isinstance(item, str):
                    text_parts.append(item)
            result = ''.join(text_parts).strip()
            if result:
                return result
    return None


def extract_sources(response):
    """Extract source URL dicts from a Mistral conversation response object.

    Returns a list of dicts with keys 'title' and 'url'.
    """
    sources = []
    if not (hasattr(response, 'outputs') and response.outputs):
        return sources
    for output in response.outputs:
        if not (hasattr(output, 'type') and output.type == 'message.output'):
            continue
        if not (hasattr(output, 'content') and output.content):
            continue
        for item in output.content:
            if hasattr(item, 'type') and item.type == 'tool_reference':
                url = getattr(item, 'url', '')
                if url:
                    sources.append({
                        'title': getattr(item, 'title', ''),
                        'url': url,
                    })
    return sources


class Mistral(callbacks.Plugin):
    """Allows use of Mistral AIs LLM API with web search capabilities"""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(Mistral, self)
        self.__parent.__init__(irc)
        self.client = None
        self.agent = None
        self._setup_client()

    def _setup_client(self):
        """Initialize the Mistral client and agent."""
        api_key = self.registryValue('apiKey')
        if not api_key:
            self.log.error("Mistral API key not configured. Please set plugins.Mistral.apiKey")
            return
        try:
            self.client = MistralClient(api_key=api_key)
        except Exception as e:
            self.log.error("Failed to initialize Mistral client: %s", repr(e))
            self.client = None
            return

        # Detect whether the installed SDK exposes agents and conversations.
        self.has_beta = getattr(self.client, 'beta', None) is not None
        self.has_agents = self.has_beta and hasattr(self.client.beta, 'agents')
        self.has_conversations = self.has_beta and hasattr(self.client.beta, 'conversations')

        if self.registryValue('enableWebSearch'):
            if not (self.has_beta and self.has_agents and self.has_conversations):
                self.log.error(
                        "Mistral SDK 'agents' functionality not available in this environment. "
                        "Ensure mistralai>=2 is installed and set plugins.Mistral.enableWebSearch "
                        "to False to disable web search."
                    )
                self.agent = None
            else:
                agent_id_cfg = self.registryValue('agentId')
                if agent_id_cfg:
                    try:
                        a = self.client.beta.agents.get(agent_id_cfg)
                        if getattr(a, 'id', None):
                            self.agent = a
                            self.log.info(
                                "Using configured Mistral agent: %s (%s)",
                                getattr(a, 'id', None),
                                getattr(a, 'name', None),
                            )
                        else:
                            self.log.info(
                                "Configured agentId %s not found; falling back to search/create.",
                                agent_id_cfg,
                            )
                            self._create_websearch_agent()
                    except Exception as e:
                        self.log.error(
                            "Could not retrieve configured agentId %s: %s",
                            agent_id_cfg,
                            repr(e),
                        )
                        self._create_websearch_agent()
                else:
                    self._create_websearch_agent()
        else:
            self.log.info("Web search disabled, using basic Mistral client")

    def _build_agent_instructions(self):
        """Return the agent instructions text from the configured prompt template.

        Falls back to a minimal hardcoded prompt if the template file is missing.
        """
        template = self.registryValue('promptTemplate')
        text = load_prompt_template(template)
        if text is None:
            self.log.warning(
                "Prompt template %r not found in %s; using built-in fallback.",
                template,
                _PROMPTS_DIR,
            )
            text = (
                "You are a helpful IRC bot. Plain text only. "
                "Keep replies under 400 characters. Be concise and direct."
            )
        return text

    def _persist_agent_id(self, agent_id):
        """Save *agent_id* to the agentId config value so it survives restarts."""
        try:
            conf.supybot.plugins.Mistral.agentId.setValue(agent_id)
            self.log.info("Persisted Mistral agent ID to config: %s", agent_id)
        except Exception as e:
            self.log.warning("Could not persist agent ID to config: %s", e)

    def _create_websearch_agent(self):
        """Create or reuse a Mistral agent with web search capabilities.

        After finding or creating an agent the ID is saved to the agentId
        config key so that subsequent restarts skip the list/create step
        entirely and go straight to beta.agents.get().
        """
        instructions = self._build_agent_instructions()
        model = self.registryValue('model')
        temperature = self.registryValue('temperature')
        desired_name = "Limnoria IRC Agent"

        try:
            try:
                agents_iter = self.client.beta.agents.list()
                for a in agents_iter:
                    if getattr(a, 'name', '').lower() == desired_name.lower():
                        self.agent = a
                        self.log.info(
                            "Found existing Mistral agent: %s (%s) — updating instructions.",
                            self.agent.id,
                            self.agent.name,
                        )
                        self._update_agent_instructions(self.agent.id, instructions, model, temperature)
                        self._persist_agent_id(self.agent.id)
                        return
            except Exception:
                self.log.info(
                    "Could not list agents (permissions or API); will attempt to create a new agent."
                )

            self.agent = self.client.beta.agents.create(
                model=model,
                description="Agent able to search information over the web for IRC chat responses",
                name=desired_name,
                instructions=instructions,
                tools=[{"type": "web_search"}],
                completion_args={
                    "temperature": temperature,
                    "top_p": 0.95,
                }
            )
            self.log.info(
                "Created Mistral websearch agent with ID: %s",
                getattr(self.agent, 'id', '<unknown>'),
            )
            self._persist_agent_id(self.agent.id)
        except Exception as e:
            extra = ""
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                extra = f", details: {e.response.text}"
            self.log.error(
                "Failed to create/reuse Mistral websearch agent: %s%s",
                repr(e),
                extra,
            )
            self.agent = None

    def _update_agent_instructions(self, agent_id, instructions, model, temperature):
        """Update an existing agent's instructions and model in place."""
        try:
            self.agent = self.client.beta.agents.update(
                agent_id=agent_id,
                instructions=instructions,
                model=model,
                completion_args={
                    "temperature": temperature,
                    "top_p": 0.95,
                }
            )
            self.log.info("Updated agent %s instructions in place.", agent_id)
        except Exception as e:
            self.log.warning(
                "Could not update agent %s in place: %s — will use existing agent as-is.",
                agent_id,
                repr(e),
            )

    def create_context_message(self, irc, msg, text, lines_of_history=None):
        """Create context from recent chat messages."""
        if lines_of_history is None:
            lines_of_history = self.registryValue('contextHistory')

        channel = msg.args[0]
        last_messages = get_last_messages(irc.state.history, channel, lines_of_history)

        context_parts = []
        if last_messages:
            context_parts.append("Recent chat context:")
            for nick, message in last_messages:
                if nick:
                    context_parts.append(f"{nick}: {message}")
                else:
                    context_parts.append(f"Bot: {message}")

        context_parts.append(f"Current question: {text}")
        return "\n".join(context_parts)

    @wrap(['text'])
    def mistral(self, irc, msg, args, text):
        """<text>

        Sends <text> to Mistral AI and returns the response. Uses web search for current information."""

        if not self.client:
            irc.reply(_("Error: Mistral client not configured. Please set the API key."))
            return

        if not self.agent and self.registryValue('enableWebSearch'):
            has_beta = getattr(self, 'has_beta', False)
            has_agents = getattr(self, 'has_agents', False)
            has_conversations = getattr(self, 'has_conversations', False)
            try:
                import mistralai as _m_pkg
                sdk_ver = getattr(_m_pkg, '__version__', '<unknown>')
            except ImportError:
                sdk_ver = '<not-importable>'

            diag = (
                f"Mistral websearch agent not available. "
                f"enableWebSearch=True; agent=None; has_beta={has_beta}; "
                f"has_agents={has_agents}; has_conversations={has_conversations}; "
                f"sdk_version={sdk_ver}. "
                f"Check bot logs or ensure mistralai>=2 is installed and the API key has agent permissions."
            )
            irc.reply(f"Error: {diag}")
            return

        channel = msg.args[0]

        try:
            context_message = self.create_context_message(irc, msg, text)

            if self.agent:
                inputs_payload = [
                    {
                        "role": "user",
                        "content": context_message,
                        "object": "entry",
                        "type": "message.input",
                    }
                ]
                try:
                    response = self.client.beta.conversations.start(
                        agent_id=self.agent.id,
                        inputs=inputs_payload,
                    )
                except Exception as agent_err:
                    err_str = str(agent_err)
                    if '404' in err_str or 'not found' in err_str.lower():
                        self.log.warning(
                            "Agent %s not found (404); clearing cached agent and falling back to chat.complete.",
                            self.agent.id,
                        )
                        self.agent = None
                        self._persist_agent_id('')
                    else:
                        raise
                if self.agent is None:
                    # Fell back after 404 — use chat.complete for this call.
                    response = self.client.chat.complete(
                        model=self.registryValue('model'),
                        messages=[
                            {"role": "system", "content": self._build_agent_instructions()},
                            {"role": "user", "content": context_message}
                        ],
                        temperature=self.registryValue('temperature')
                    )
                    response_text = response.choices[0].message.content if response.choices else None
                    sources = []
                else:
                    response_text = extract_response_text(response)
                    if response_text is None:
                        self.log.error("extract_response_text returned None for response: %s", repr(response))
                    sources = extract_sources(response)
            else:
                response = self.client.chat.complete(
                    model=self.registryValue('model'),
                    messages=[
                        {"role": "system", "content": self._build_agent_instructions()},
                        {"role": "user", "content": context_message}
                    ],
                    temperature=self.registryValue('temperature')
                )
                response_text = response.choices[0].message.content if response.choices else None
                sources = []

            if response_text:
                max_length = self.registryValue('maxResponseLength')
                if len(response_text) > max_length:
                    response_text = response_text[:max_length - 3] + "..."

                if sources:
                    source_urls = [src['url'] for src in sources[:2]]
                    response_text += f" (sources: {', '.join(source_urls)})"

                irc.reply(response_text)
            else:
                irc.reply(_("Error: No response from Mistral AI."))

        except Exception as e:
            self.log.error("Error calling Mistral API: %s", e)
            irc.reply(f"Error: Failed to get response from Mistral AI: {e}")

    @wrap([])
    def mistralreload(self, irc, msg, args):
        """(takes no arguments)

        Reloads the prompt template and updates the Mistral agent instructions
        in place. Use after changing supybot.plugins.Mistral.promptTemplate."""

        if not self.client:
            irc.reply(_("Error: Mistral client not configured."))
            return

        if not (self.has_beta and self.has_agents):
            irc.reply(_("Error: Agent API not available. Enable web search and check your API key."))
            return

        agent_id = self.registryValue('agentId')
        instructions = self._build_agent_instructions()
        model = self.registryValue('model')
        temperature = self.registryValue('temperature')

        if agent_id:
            self._update_agent_instructions(agent_id, instructions, model, temperature)
            template = self.registryValue('promptTemplate')
            irc.reply(f"Agent {agent_id} updated with template '{template}'.")
        else:
            self._create_websearch_agent()
            if self.agent:
                template = self.registryValue('promptTemplate')
                irc.reply(f"Agent created ({self.agent.id}) with template '{template}'.")
            else:
                irc.reply(_("Error: Failed to create agent. Check bot logs."))

    def die(self):
        """Clean up when the plugin is unloaded."""
        self.__parent.die()


Class = Mistral
