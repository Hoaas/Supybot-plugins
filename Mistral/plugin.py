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

from supybot import utils, plugins, ircutils, callbacks, conf
from supybot.commands import *
from supybot.i18n import PluginInternationalization
from mistralai import Mistral as MistralClient
import re


_ = PluginInternationalization('Mistral')


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
        """Initialize the Mistral client and agent"""
        api_key = self.registryValue('apiKey')
        if not api_key:
            self.log.error("Mistral API key not configured. Please set plugins.Mistral.apiKey")
            return
        try:
            # Initialize client
            self.client = MistralClient(api_key=api_key)
        except Exception as e:
            self.log.error(f"Failed to initialize Mistral client: {repr(e)}")
            self.client = None
            return

        # Detect whether the installed SDK exposes the agents and conversations features
        # Record flags on the instance for later diagnostics
        self.has_beta = getattr(self.client, 'beta', None) is not None
        self.has_agents = False
        self.has_conversations = False

        if self.has_beta:
            try:
                self.has_agents = hasattr(self.client.beta, 'agents')
            except Exception:
                self.has_agents = False
            try:
                self.has_conversations = hasattr(self.client.beta, 'conversations')
            except Exception:
                self.has_conversations = False
        # Note: use instance flags (self.has_beta, self.has_agents, self.has_conversations)

        if self.registryValue('enableWebSearch'):
            if not (self.has_beta and self.has_agents and self.has_conversations):
                self.log.error("Mistral SDK 'agents' functionality not available in this environment. "
                               "Install the agents extra with: pip install 'mistralai[agents]' "
                               "or set plugins.Mistral.enableWebSearch to False to disable web search.")
                self.agent = None
            else:
                # If an explicit agentId is configured, try to fetch that agent first
                try:
                    agent_id_cfg = self.registryValue('agentId')
                except Exception:
                    agent_id_cfg = None

                if agent_id_cfg:
                    try:
                        a = self.client.beta.agents.get(agent_id_cfg)
                        if getattr(a, 'id', None):
                            self.agent = a
                            self.log.info(f"Using configured Mistral agent: {getattr(a,'id',None)} ({getattr(a,'name',None)})")
                        else:
                            self.log.info(f"Configured agentId {agent_id_cfg} not found; falling back to search/create.")
                            self._create_websearch_agent()
                    except Exception as e:
                        self.log.error(f"Could not retrieve configured agentId {agent_id_cfg}: {repr(e)}")
                        self._create_websearch_agent()
                else:
                    self._create_websearch_agent()
        else:
            self.log.info("Web search disabled, using basic Mistral client")

    def _create_websearch_agent(self):
        """Create or reuse a Mistral agent with web search capabilities"""
        try:
            model = self.registryValue('model')
            temperature = self.registryValue('temperature')
            desired_name = "Limnoria IRC Agent"

            # Look for an existing agent with the desired name and reuse it if found.
            try:
                agents_iter = self.client.beta.agents.list()
                for a in agents_iter:
                    name = getattr(a, 'name', None)
                    if name and name.lower() == desired_name.lower():
                        self.agent = a
                        self.log.info(f"Reusing existing Mistral agent: {self.agent.id} ({self.agent.name})")
                        return
            except Exception:
                # Listing may not be supported or may fail for some clients/permissions; continue to create.
                self.log.info("Could not list agents (permissions or API); will attempt to create a new agent.")

            # Not found -> create new persistent agent on Mistral side
            self.agent = self.client.beta.agents.create(
                model=model,
                description="Agent able to search information over the web for IRC chat responses",
                name=desired_name,
                instructions=(
                    "You are an IRC bot assistant. Provide concise, helpful responses to user queries. "
                    "Use web search when you need current information. Keep responses under 400 characters "
                    "when possible for IRC. Be conversational and friendly."
                ),
                tools=[{"type": "web_search"}],
                completion_args={
                    "temperature": temperature,
                    "top_p": 0.95,
                }
            )
            self.log.info(f"Created Mistral websearch agent with ID: {getattr(self.agent,'id','<unknown>')}")
        except Exception as e:
            # Try to surface HTTP/status info when present
            try:
                extra = f", details: {e.response.text}" if hasattr(e, 'response') and hasattr(e.response, 'text') else ""
            except Exception:
                extra = ""
            self.log.error(f"Failed to create/reuse Mistral websearch agent: {repr(e)}{extra}")
            self.agent = None

    def get_last_messages(self, irc, channel, number):
        """Get the last N messages from the channel for context"""
        messages = []
        
        messages_in_channel = filter(
            lambda x: x.channel == channel and x.command == 'PRIVMSG', 
            reversed(irc.state.history)
        )
        
        # Only last messages, but not the command that triggered this
        messages_in_channel = reversed(list(messages_in_channel)[1:number])
        
        for m in messages_in_channel:
            nick = m.nick
            # Remove IRC formatting
            message = ircutils.stripFormatting(m.args[1])
            messages.append((nick, message))
        
        return messages

    def create_context_message(self, irc, msg, text, lines_of_history=None):
        """Create context from recent chat messages"""
        if lines_of_history is None:
            lines_of_history = self.registryValue('contextHistory')
            
        channel = msg.args[0]
        last_messages = self.get_last_messages(irc, channel, lines_of_history)
        
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
            irc.reply("Error: Mistral client not configured. Please set the API key.")
            return
            
        if not self.agent and self.registryValue('enableWebSearch'):
            # Provide inline diagnostics to help debug environment vs permissions
            has_beta = getattr(self, 'has_beta', False)
            has_agents = getattr(self, 'has_agents', False)
            has_conversations = getattr(self, 'has_conversations', False)
            try:
                import mistralai as _m_pkg
                sdk_ver = getattr(_m_pkg, '__version__', '<unknown>')
            except Exception:
                sdk_ver = '<not-importable>'

            diag = (
                "Mistral websearch agent not available. "
                f"enableWebSearch=True; agent=None; has_beta={has_beta}; has_agents={has_agents}; has_conversations={has_conversations}; sdk_version={sdk_ver}. "
                "Check bot logs or ensure 'mistralai[agents]' is installed and the API key has agent permissions."
            )
            irc.reply(f"Error: {diag}")
            return
        
        try:
            # Create context from recent messages
            context_message = self.create_context_message(irc, msg, text)

            if self.agent:
                # Use websearch agent
                # Prepare inputs in the agent conversation expected format
                # Prefer structured message entries as in the API examples
                inputs_payload = [
                    {
                        "role": "user",
                        "content": context_message,
                        "object": "entry",
                        "type": "message.input",
                    }
                ]

                response = self.client.beta.conversations.start(
                    agent_id=self.agent.id,
                    inputs=inputs_payload,
                    stream=False,
                )

                # Extract the response text
                response_text = self._extract_response_text(response)
                sources = self._extract_sources(response)
            else:
                # Use basic chat completion without websearch
                response = self.client.chat.complete(
                    model=self.registryValue('model'),
                    messages=[
                        {"role": "system", "content": "You are a helpful IRC bot assistant. Keep responses concise."},
                        {"role": "user", "content": context_message}
                    ],
                    temperature=self.registryValue('temperature')
                )

                response_text = response.choices[0].message.content if response.choices else None
                sources = []
            
            if response_text:
                # Limit response length for IRC
                max_length = self.registryValue('maxResponseLength')
                if len(response_text) > max_length:
                    response_text = response_text[:max_length-3] + "..."
                
                # Add sources if available
                if sources:
                    source_urls = [src['url'] for src in sources[:2]]  # Limit to 2 sources
                    response_text += f" (sources: {', '.join(source_urls)})"
                
                irc.reply(response_text)
            else:
                irc.reply("Error: No response from Mistral AI.")
                
        except Exception as e:
            self.log.error(f"Error calling Mistral API: {e}")
            irc.reply(f"Error: Failed to get response from Mistral AI: {str(e)}")

    def _extract_response_text(self, response):
        """Extract the main text response from Mistral API response"""
        try:
            if hasattr(response, 'outputs') and response.outputs:
                for output in response.outputs:
                    if hasattr(output, 'type') and output.type == 'message.output':
                        if hasattr(output, 'content') and output.content:
                            # Handle case where content is directly a string
                            if isinstance(output.content, str):
                                return output.content.strip()
                            # Handle case where content is a list of content items
                            elif isinstance(output.content, list):
                                text_parts = []
                                for content_item in output.content:
                                    if hasattr(content_item, 'type') and content_item.type == 'text':
                                        if hasattr(content_item, 'text'):
                                            text_parts.append(content_item.text)
                                    elif isinstance(content_item, str):
                                        text_parts.append(content_item)
                                return ''.join(text_parts).strip()
        except Exception as e:
            self.log.error(f"Error extracting response text: {e}")
        return None

    def _extract_sources(self, response):
        """Extract source URLs from Mistral API response"""
        sources = []
        try:
            if hasattr(response, 'outputs') and response.outputs:
                for output in response.outputs:
                    if hasattr(output, 'type') and output.type == 'message.output':
                        if hasattr(output, 'content') and output.content:
                            for content_item in output.content:
                                if (hasattr(content_item, 'type') and 
                                    content_item.type == 'tool_reference'):
                                    source_info = {
                                        'title': getattr(content_item, 'title', ''),
                                        'url': getattr(content_item, 'url', ''),
                                        'source': getattr(content_item, 'source', '')
                                    }
                                    if source_info['url']:
                                        sources.append(source_info)
        except Exception as e:
            self.log.error(f"Error extracting sources: {e}")
        return sources


    def die(self):
        """Clean up when the plugin is unloaded"""
        if self.client:
            try:
                # Clean up any resources if needed
                pass
            except Exception as e:
                self.log.error(f"Error during cleanup: {e}")
        self.__parent.die()

    


Class = Mistral


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
