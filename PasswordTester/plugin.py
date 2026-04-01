###
# Copyright (c) 2018, Terje Hoås
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

import hashlib

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization, internationalizeDocstring
    _ = PluginInternationalization('PasswordTester')
except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f


def hashPassword(password):
    """Return a (prefix, suffix) tuple of the SHA1 hash of password.

    prefix is the first 5 hex characters (lowercase), suffix is the
    remainder uppercased — matching the HIBP k-anonymity API format.
    """
    digest = hashlib.sha1(password.encode()).hexdigest()
    return digest[:5], digest[5:].upper()


def parseHibpResponse(text, suffix):
    """Parse a HIBP range-API response and return the breach count for suffix.

    text is the decoded response body (lines of 'SUFFIX:COUNT').
    suffix is the uppercase hex tail to look up.
    Returns the count as an int, or 0 if the suffix is not found.
    """
    for line in text.splitlines():
        parts = line.split(':')
        if len(parts) == 2 and parts[0].strip().upper() == suffix:
            try:
                return int(parts[1].strip())
            except ValueError:
                return 0
    return 0


_HIBP_URL = 'https://api.pwnedpasswords.com/range/'


class PasswordTester(callbacks.Plugin):
    """Checks a password against the HaveIBeenPwned Pwned Passwords API."""
    threaded = True

    @wrap(['text'])
    @internationalizeDocstring
    def password(self, irc, msg, args, password):
        """<password>

        Returns if and how many times this password has been seen in data breaches."""
        prefix, suffix = hashPassword(password)
        try:
            response = utils.web.getUrl(_HIBP_URL + prefix)
            text = response.decode('ascii', 'ignore').strip()
        except Exception as e:
            self.log.warning('HIBP lookup failed: %s', e)
            irc.reply(_('The call to HIBP failed. Unable to check password status at this time.'))
            return

        count = parseHibpResponse(text, suffix)
        if count:
            irc.reply(_('This password has been seen {count} times in data breaches.').format(count=count))
        else:
            irc.reply(_('This password has not been seen in any known data breaches.'))


Class = PasswordTester
