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
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('PasswordTester')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


class PasswordTester(callbacks.Plugin):
    """Checks if the given string is in Troy Hunts HaveIBeenPwned.com API."""
    threaded = True

    url = "https://api.pwnedpasswords.com/range/"

    @wrap(['text'])
    def password(self, irc, msg, args, password):
        """<password>

        Returns if and how many times this password has been in data breaches."""

        sha1 = hashlib.sha1(password.encode()).hexdigest()
        sha1_prefix = sha1[:5]
        sha1_suffix = sha1[5:].upper()

        try:
            response = utils.web.getUrl(self.url + sha1_prefix)
            text = response.decode('ascii', 'ignore').strip()
            if sha1_suffix in text:
                # Password is pwned
                frequency = [s for s in text.splitlines() if sha1_suffix in s][0].split(':')[1]
                irc.reply("This password has been present %s times in data breaches." % frequency)
                return
            else:
                irc.reply("Password is safe to use!")
                return
        except:
            irc.reply("The call to HIBP failed in some way. Unable to check password status at this time.")
            return


Class = PasswordTester


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
