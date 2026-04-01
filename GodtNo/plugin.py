###
# Copyright (c) 2022, Terje Hoås
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

import json

import supybot.utils as utils
from supybot.commands import *
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('GodtNo')
except ImportError:
    _ = lambda x: x


def formatRecipe(data):
    """Parse a godt.no GraphQL JSON response and return a formatted string.

    Returns a string on success, or None if the response contains no recipe.
    data may be bytes or str.
    """
    if isinstance(data, bytes):
        data = data.decode()
    j = json.loads(data)
    randomRecipe = j.get('data', {}).get('randomRecipe')
    if randomRecipe is None:
        return None
    title = randomRecipe.get('title', '').strip()
    cookingTime = randomRecipe.get('cookingTime')
    relativeUrl = randomRecipe.get('links', {}).get('relativeUrl', '')
    if cookingTime is not None:
        return f'{title} ({cookingTime} minutter) - https://godt.no{relativeUrl}'
    return f'{title} - https://godt.no{relativeUrl}'


class GodtNo(callbacks.Plugin):
    """Get random dinner recipe from godt.no - Norwegian only"""
    threaded = True

    @wrap([])
    def middag(self, irc, msg, args):
        """takes no arguments

        Returns a random dinner recipe from godt.no."""
        url = 'https://www.godt.no/api/graphql'
        query = ('query randomRecipe($input: RandomlySortedSearchInput!) {'
                 ' randomRecipe(input: $input) { id title cookingTime links { relativeUrl } } }')
        payload = json.dumps({
            'operationName': 'randomRecipe',
            'variables': {
                'input': {
                    'filter': [
                        {'field': 'status', 'value': 'published'},
                        {'field': 'tag_id', 'value': '8'},
                    ]
                }
            },
            'query': query,
        }).encode()
        headers = {
            'User-Agent': 'https://github.com/Hoaas/Supybot-plugins',
            'Content-Type': 'application/json',
            'apollo-require-preflight': 'true',
        }

        try:
            data = utils.web.getUrl(url, headers=headers, data=payload)
            result = formatRecipe(data)
        except Exception as e:
            self.log.error('GodtNo: failed to fetch recipe: %s', e)
            irc.error(_('Could not fetch a recipe from godt.no.'))
            return

        if result is None:
            irc.error(_('Could not fetch a recipe from godt.no.'))
            return

        irc.reply(result)


Class = GodtNo
