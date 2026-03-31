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

import re
import json
import time
import os.path

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization, internationalizeDocstring
    _ = PluginInternationalization('AutoOp')
except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f


def dbPath(channel):
    """Return the path to the AutoOp database file for the given channel."""
    dataDir = conf.supybot.directories.data
    chanDir = dataDir.dirize(channel.lower())
    if not os.path.exists(chanDir):
        os.makedirs(chanDir)
    return dataDir.dirize(f'{channel.lower()}/AutoOp.db')


def readDb(channel):
    """Read the AutoOp database for a channel.

    Returns a dict mapping hostmask regex → mode, or an empty dict if the
    database does not exist yet. Raises IOError on read failure.
    """
    path = dbPath(channel)
    if not os.path.isfile(path):
        return {}
    with open(path, 'r') as fd:
        try:
            return json.load(fd)
        except json.JSONDecodeError:
            return {}


def writeDb(channel, hostdict):
    """Write the AutoOp database for a channel.

    Raises IOError on write failure.
    """
    path = dbPath(channel)
    with open(path, 'w') as fd:
        json.dump(hostdict, fd)


def addEntry(channel, hostmask, mode):
    """Add a hostmask→mode entry to the database.

    Returns True on success, 'exists' if the regex is already present,
    or 'invalid' if the hostmask is not a valid regex.
    """
    try:
        re.compile(hostmask)
    except re.error:
        return 'invalid'

    hostdict = readDb(channel)
    if hostmask in hostdict:
        return 'exists'

    hostdict[hostmask] = mode
    writeDb(channel, hostdict)
    return True


def matchingUsers(irc, channel, hostdict):
    """Return (oplist, halfoplist, voicelist) of nicks that match the database
    but do not yet have the corresponding mode in the given channel.
    """
    oplist, halfoplist, voicelist = [], [], []
    chanState = irc.state.channels[channel]
    for nick in chanState.users:
        hostname = irc.state.nickToHostmask(nick)
        for regex, mode in hostdict.items():
            if re.fullmatch(regex, hostname):
                if mode == 'op' and nick not in chanState.ops:
                    oplist.append(nick)
                elif mode == 'halfop' and nick not in chanState.halfops:
                    halfoplist.append(nick)
                elif mode == 'voice' and nick not in chanState.voices:
                    voicelist.append(nick)
                break
    return oplist, halfoplist, voicelist


class AutoOp(callbacks.Plugin):
    """Auto-op/halfop/voice users based on hostmask regex matching.

    Use autoop, autohalfop, or autovoice to register a nick or hostmask
    (regex) for automatic mode assignment on join.
    """
    threaded = True

    def _automode(self, irc, msg, channel, user, mode):
        """Add a hostmask to the database and immediately apply modes."""
        # Resolve nick to hostmask if the nick is present in the channel.
        if irc.isNick(user) and user in irc.state.channels[msg.args[0]].users:
            hostmask = irc.state.nickToHostmask(user)
            # Escape all regex metacharacters so the pattern matches literally.
            hostmask = re.escape(hostmask)
        else:
            hostmask = user

        result = addEntry(channel, hostmask, mode)
        if result == 'invalid':
            irc.error(_('Not a valid regex for hostmask.'))
            return
        if result == 'exists':
            irc.error(_('Regex already in database.'))
            return

        self.log.info('AutoOp: adding %s in %s as %s', hostmask, channel, mode)
        irc.replySuccess()
        self._applyModes(irc, channel)

    def _applyModes(self, irc, channel):
        """Apply pending auto-modes to all users currently in the channel."""
        if irc.nick not in irc.state.channels[channel].ops:
            return

        try:
            hostdict = readDb(channel)
        except IOError:
            self.log.warning('AutoOp: could not read database for %s', channel)
            return

        oplist, halfoplist, voicelist = matchingUsers(irc, channel, hostdict)

        maxmodes = 4
        for nicks, msgfn in (
            (oplist, ircmsgs.ops),
            (halfoplist, ircmsgs.halfops),
            (voicelist, ircmsgs.voices),
        ):
            while nicks:
                irc.queueMsg(msgfn(channel, nicks[:maxmodes]))
                nicks = nicks[maxmodes:]

        irc.noReply()

    @wrap([('checkCapability', 'owner'), 'channeldb', 'anything'])
    @internationalizeDocstring
    def autoop(self, irc, msg, args, channel, user):
        """[<channel>] <nick|hostmask>

        Adds the nick's hostmask (or a literal hostmask/regex) to the
        auto-op list for the channel.
        """
        self._automode(irc, msg, channel, user, 'op')

    @wrap([('checkCapability', 'owner'), 'channeldb', 'anything'])
    @internationalizeDocstring
    def autohalfop(self, irc, msg, args, channel, user):
        """[<channel>] <nick|hostmask>

        Adds the nick's hostmask (or a literal hostmask/regex) to the
        auto-halfop list for the channel.
        """
        self._automode(irc, msg, channel, user, 'halfop')

    @wrap([('checkCapability', 'owner'), 'channeldb', 'anything'])
    @internationalizeDocstring
    def autovoice(self, irc, msg, args, channel, user):
        """[<channel>] <nick|hostmask>

        Adds the nick's hostmask (or a literal hostmask/regex) to the
        auto-voice list for the channel.
        """
        self._automode(irc, msg, channel, user, 'voice')

    def doJoin(self, irc, msg):
        time.sleep(2)
        channel = msg.args[0]
        if channel not in irc.state.channels:
            return
        self._applyModes(irc, channel)

Class = AutoOp
