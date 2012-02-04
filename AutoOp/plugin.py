# coding=utf8
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
import os.path
import simplejson
import supybot.ircdb as ircdb
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class AutoOp(callbacks.Plugin):
    """This plugin autoop/halfop/voice depending on hostmask. The only command
    is autoop (for adding hostmasks). WARNING: Very not thread safe. Several
    commands issued at the same time will overwrite each other."""
    
    def autovoice(self, irc, msg, args, channel, user):
        """[<channel>] <nick|hostmask>
        Adds (nicks) hostmask to the autoop list. Hostmask can be a regex.
        """
        self._automode(irc, msg, channel, user, "voice")
    autovoice = wrap(autovoice, [('checkCapability', 'owner'), 'channeldb', 'anything'])
    
    def autohalfop(self, irc, msg, args, channel, user):
        """[<channel>] <nick|hostmask>
        Adds (nicks) hostmask to the autoop list. Hostmask can be a regex.
        """
        self._automode(irc, msg, channel, user, "halfop")
    autohalfop = wrap(autohalfop, [('checkCapability', 'owner'), 'channeldb', 'anything'])

    def autoop(self, irc, msg, args, channel, user):
        """[<channel>] <nick|hostmask>
        Adds (nicks) hostmask to the autoop list. Hostmask can be a regex.
        """
        self._automode(irc, msg, channel, user, "op")
    autoop = wrap(autoop, [('checkCapability', 'owner'), 'channeldb', "anything"])

    """Takes in a nickname or hostmask and a mode and adds it to the database
    if it isn't already added."""
    def _automode(self, irc, msg, channel, user, mode):
        hostmask = ""
        # If it is a valid nick and currently in the channel
        if ( irc.isNick(user) and user in
                irc.state.channels[msg.args[0]].users ):
            hostmask = irc.state.nickToHostmask(user)
        # assume it is a hostmask, and check that
        else:
            hostmask = user
        # Add the hostmask to file. Returns True on success.
        ret = self._writeToFile(channel, hostmask, mode)
        self._autoMagic(irc, msg, channel)
        if ret == -1:
            irc.reply("Not a valid regex for hostmask :(:(")
            return
        elif ret == -2: 
            irc.reply("Regex already in database.")
            return
        elif ret == -3:
            irc.reply("Cannot read and/or write (to) database.")
            return
        # Check if any users in the channel match the hostmasks added.

    def _autoMagic(self, irc, msg, channel):
        # If bot does not got op
        if irc.nick not in irc.state.channels[channel].ops:
            return
        # Read database
        hostdict, _ = self._readFile(channel)

        # If for some reason _readFile() failed 
        if hostdict == -3:
            return -3
        elif hostdict == -2:
            return -2
        elif hostdict == -1:
            return -1

        # List of those nicks that are to gain modes
        oplist = []
        halfoplist = []
        voicelist = []

        # For all nicks in channel
        for u in irc.state.channels[channel].users:
            hostname = irc.state.nickToHostmask(u)
            for regex in hostdict.iteritems():
                match = re.search(regex[0], hostname)
                if match:
                    if regex[1] == "op":
                        if u not in irc.state.channels[channel].ops:
                            oplist.append(u)
                    elif regex[1] == "halfop":
                        if u not in irc.state.channels[channel].halfops:
                            halfoplist.append(u)
                    elif regex[1] == "voice":
                        if u not in irc.state.channels[channel].voices:
                            voicelist.append(u)
  
        maxmodes = 4
 
        # While there are still people to give op to
        while len(oplist) > 0:
            # Op the first 4, or whatever maxmode is
            irc.queueMsg(ircmsgs.ops(channel, oplist[:maxmodes]))
            # Remove those that have been given op from the list
            oplist = oplist[maxmodes:]
            # If the list is shorter than maxmode, op them all.
            if len(oplist) <= maxmodes:
                irc.queueMsg(ircmsgs.ops(channel, oplist))
                break;
                    
        while len(halfoplist) > 0:
            irc.queueMsg(ircmsgs.halfops(channel, halfoplist[:maxmodes]))
            halfoplist = halfoplist[maxmodes:]
            if len(halfoplist) <= maxmodes:
                irc.queueMsg(ircmsgs.halfops(channel, halfoplist))
                break;
                    
        while len(voicelist) > 0:
            irc.queueMsg(ircmsgs.voices(channel, voicelist[:maxmodes]))
            voicelist = voicelist[maxmodes:]
            if len(voicelist) <= maxmodes:
                irc.queueMsg(ircmsgs.voices(channel, voicelist))
                break;

        # Can't really remember that this does.
        irc.noReply()

    # Whe the bot is oped we want to check all the hosts in the channel and op those that should have op.
    def doMode(self, irc, msg):
        channel = msg.args[0]
        self._autoMagic(irc, msg, channel) 
 
    def doJoin(self, irc, msg):
        channel = msg.args[0]
        self._autoMagic(irc, msg, channel)

    def _readFile(self, channel):
        # Check if db file exists, create if it doesn't.
        dataDir = conf.supybot.directories.data
        channel = channel.lower()
        chandir = dataDir.dirize(channel)

        if not os.path.exists(chandir):
            os.makedirs(chandir)

        dataDir = dataDir.dirize(channel + "/AutoOp.db")
        if not os.path.isfile(dataDir):
            # I believe this overwrites if the file exists
            self.log.info("AutoOp: Creating new database at " + dataDir)
            try:
                open(dataDir, 'w')
            except IOError:
                return -3, -3
        # db exists now.
        try:
            logfile = open(dataDir, 'r')
        except  IOError:
            return -3, -3
        hostdict = {}
        try:
            hostdict = simplejson.load(logfile)
            # self.log.info("DEBUG: " + str(json))
        except simplejson.JSONDecodeError, j:
            pass # Happens when the file doesn't exist.
        logfile.close()
        return hostdict, dataDir

    def _writeToFile(self, channel, hostmask, mode):
        hostdict, dataDir = self._readFile(channel)
        
        # In case of -3, db could not be accessed.
        if hostdict == -3:
            return -3

        # If hostmask already exists there is no need to add it.
        if (hostmask in hostdict):
            return -2

        # Write dictionary to file again
        logfile = open(dataDir, 'w')
        hostdict[hostmask] = mode
        self.log.info("AutoOp: Adding " + hostmask + " in " + channel + " to database as " + mode + ".")
        logfile.write(simplejson.dumps(hostdict))

    def _autoMode(self, channel, hostmask):
        dataDir = conf.supybot.directories.data
        channel = channel.lower()
        chandir = dataDir.dirize(channel)
        
        if not os.path.exists(chandir):
            return False
            
        dataDir = dataDir.dirize(channel + "/AutoOp.db")
        
        logfile = open(dataDir, 'r')
        # Reads the current log
        log = logfile.read()
        lines = log.splitlines()
        
        for l in lines:
	        # Incase of extra whitespace at input
    	    l = l.strip()
            regexline = l.split("#")
    	    # Split up the hostmask and v/h/o, ignore whatever comment might be present
    	    maskandmode = regexline[0].split()
            regexmask = maskandmode[0]
    	    mode = maskandmode[1]
    	    
    	    # The first mode that matches the regex is always retured. 
    	    # So if you want to ignore a host add it first with an invalid mode.
            if(re.match(regexmask, hostmask) is not None):
                return mode
        return False

Class = AutoOp


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
