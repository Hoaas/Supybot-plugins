###
# Copyright (c) 2013, Terje Hoås
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

from . import pysnap

import datetime
import os.path
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.schedule as schedule
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('SupySnap')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

class SupySnap(callbacks.Plugin):
    """Add the help for "@plugin help SupySnap" here
    This should describe *how* to use this plugin."""
    threaded = True
    _names = []

    def register(self, irc, msg, args, channel, username, password, email, birthday):
        """[channel] <username> <password> <email> <birthday>

        Registers the given username as a snapchat account. Stores username and
        password for the given channel. Birthday needs to be on the form
        yyyy-mm-dd."""
        if email.find('@') == -1:
            irc.error('That doesn\'t look like an email address')
            return
        try:
            datetime.datetime.strptime(birthday, '%Y-%m-%d')
        except ValueError:
            irc.error('Birthday must be on the format YYYY-MM-DD.')
            return
        s = pysnap.Snapchat()
        reg = s.register(username, password, email, birthday)
        if not reg:
            irc.error('Could not register.')
            return
        irc.reply('Account created! Now do "Config channel supybot.plugins.SupySnap.username {0}" and "Config channel supybot.plugins.SupySnap.password {1}".'.format(username, password))
    register = wrap(register, ['channel', 'somethingWithoutSpaces', 'somethingWithoutSpaces', 'somethingWithoutSpaces', 'somethingWithoutSpaces'])

    def start(self, irc, msg, args, channel):
        """[channel]

        Starts SupySnap for [channel]. If [channel] is not specified the
        current one is used."""

        seconds = self.registryValue('interval', channel)
        username = self.registryValue('username', channel)
        password = self.registryValue('password', channel)
        address = self.registryValue('address', channel)
        localpath = self.registryValue('localpath', channel)

        if not username or username == '':
            irc.error('No username entered.')
            return
        if not password or password == '':
            irc.error('No password entered.')
            return
        if not address or address == '':
            irc.error('No address entered.')
            return
        if not localpath or localpath == '':
            irc.error('No local path entered.')
            return
        if not os.path.isdir(localpath):
            os.makedirs(localpath)


        name = "supysnap_" + channel
        def fetch():
            try:
                s = pysnap.Snapchat()
                if not s.login(username, password).get('logged'):
                    irc.reply('Invalid username or password.')
                    return
                for snap in s.get_snaps():
                    filename = '{0}_{1}.{2}'.format(snap['sender'], snap['id'], pysnap.get_file_extension(snap['media_type']))
                    abspath = os.path.abspath(os.path.join(localpath, filename))
                    if os.path.isfile(abspath):
                        continue
                    data = s.get_blob(snap['id'])
                    if data is None:
                        continue
                    with open(abspath, 'wb') as f:
                        f.write(data)
                        irc.reply('[{0}] New snap from: {1}! - {2}{3}'.format(username, snap['sender'], address, filename))
                    # if markasread:
                        # s.mark_view(snap['id'])
            except Exception as e:
                self.log.error('SupySnap: + ' + str(e))


        self._names.append(name)
        try:
            schedule.addPeriodicEvent(fetch, seconds, name)
        except AssertionError:
            irc.error('SupySnap is already running in this channel.')
            return
        irc.replySuccess()
    start = wrap(start, ['channel', 'admin'])

    def stop(self, irc, msg, args, channel):
        """[channel]

        Stops SupySnap for [channel]. If [channel] is not specified the 
        current one is used."""
        name = "supysnap_" + channel
        try:
            self._names.remove(name)
        except:
            pass
        try:
            schedule.removeEvent(name)
        except KeyError:
            irc.error('SupySnap was not running for this channel.')
            return
        irc.replySuccess()
    stop = wrap(stop, ['channel', 'admin'])

    def die(self):
        for name in self._names:
            try:
                schedule.removeEvent(name)
            except KeyError:
                pass
        self._names = []

#{'id': '449042378662886327r',
# 'media_id': None,
# 'media_type': 0,
# 'opened': 1378662886327,
# 'recipient': None,
# 'screenshot_count': None,
# 'sender': 'teamsnapchat',
# 'sent': 1378662886327,
# 'status': 2,
# 'time': None}

Class = SupySnap


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
