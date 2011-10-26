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
import supybot.ircdb as ircdb
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class AutoOp(callbacks.Plugin):
    """This plugin autoop/halfop/voice depending on hostmask. The only command is autoop (for adding hostmasks)."""
    threaded = True
    
    def autoop(self, irc, msg, args, channel, hostmask):
        """[<channel>] <regex for hostmask> <op|voice|halfop> [<#comment>] 
        
        Comment is only visible in the database file.
        Adds hostmask to the autoop list. Make sure it is correct regex. There is no error check on this.
        Be very careful when using this command. Might be better to edit the file manually.
        """
        self.log.info("Adding hostmask: " + hostmask + " for channel " + channel)
        self._addHostMask(channel, hostmask)
    autoop = wrap(autoop, [('checkCapability', 'owner'), 'channeldb', 'text'])

    # Whe the bot is oped we want to check all the hosts in the channel and op those that should have op.
    def doMode(self, irc, msg):
        channel = msg.args[0]
        # modes = msg.args[1]
        targets = msg.args[2:]
        # All oped targets
        for t in targets:
            # If bot is target of the mode change
            if(irc.nick == t):
                if irc.nick in irc.state.channels[channel].ops:                                
                    # Bot have gained op!
                    
                    # List to contains nick that are getting the appropriate mode
                    oplist = []
                    halfoplist = []
                    voicelist = []
                    
                    for u in irc.state.channels[channel].users:
                        # Ignore those that have op
                        if u not in irc.state.channels[channel].ops:
                            
                            host =  irc.state.nickToHostmask(u).split("@")[1]
                            mode = self._autoMode(channel, host)
                            if(mode == "voice" or mode == "op" or mode == "halfop"):
                                if mode == "op":
                                    oplist.append(u)
                                elif mode == "voice":
                                    voicelist.appen(u)
                                elif mode == "halfop":
                                    halfoplist.append(u)
                                self.log.info("AutoOp: Auto" + mode + " to " + u + " (" + host + ")")
                            elif(mode != False):
                                self.log.warning("AutoOp: Hostmask hit for " + u + " (" + host + "), but unknow mode.")
                            else:
                                self.log.debug("AutoOp: No match for " + u + " (" + host + ").")
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
                        irc.queueMsg(ircmsgs.ops(channel, halfoplist[:maxmodes]))
                        halfoplist = halfoplist[maxmodes:]
                        if len(halfoplist) <= maxmodes:
                            irc.queueMsg(ircmsgs.ops(channel, halfoplist))
                            break;
                    
                    while len(voicelist) > 0:
                        irc.queueMsg(ircmsgs.ops(channel, voicelist[:maxmodes]))
                        oplist = voicelist[maxmodes:]
                        if len(voicelist) <= maxmodes:
                            irc.queueMsg(ircmsgs.ops(channel, voicelist))
                            break;
                        
                    # Can't really remember that this does.
                    irc.noReply()
                                               
                                                
    def doJoin(self, irc, msg):
        channel = msg.args[0]
        if irc.nick in irc.state.channels[channel].ops:
            mode = self._autoMode(channel, msg.host)
            if(mode == "voice" or mode == "op" or mode == "halfop"):
                if mode == "op":
                    modemsg = ircmsgs.op(channel, msg.nick)
                elif mode == "voice":
                    modemsg = ircmsgs.voice(channel, msg.nick)
                elif mode == "halfop":
                    modemsg = ircmsgs.halfop(channel, msg.nick)
                irc.queueMsg(modemsg)
                irc.noReply()
	        self.log.info("AutoOp: Auto" + mode + " to " + msg.nick + " (" + msg.host + ")")
	    elif(mode != False):
                selg.log.warning("AutoOp: Hostmask hit for " + msg.nick + " (" + msg.host + "), but unknown mode.")
            else:
                self.log.debug("AutoOp: No match on " + msg.nick + " (" + msg.host + ").")
        else:
           # If the bot don't got op, perhaps say something now and then?
           pass
            
    def _addHostMask(self, channel, hostmask):
        dataDir = conf.supybot.directories.data
        channel = channel.lower()
        chandir = dataDir.dirize(channel)
        
        if not os.path.exists(chandir):
            os.makedirs(chandir)
            
        dataDir = dataDir.dirize(channel + "/AutoOp.db")
        if not os.path.isfile(dataDir):
            # I believe this overwrites if the file exists
            open(dataDir, 'w')
         
        # a for append   
        logfile = open(dataDir, 'a')
        logfile.write(hostmask + '\n')

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
