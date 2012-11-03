#!/usr/local/bin/python
#-*- coding: utf8 -*-
###
# Copyright (c) 2000, 2006 Tom Morton, Sebastien Dailly
# Copyright (c) 2010, Nicolas Coevoet
# Ohgod I'm not good with copyright. Changed in 2012 by Terje Hoås
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#        
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.ircmsgs as ircmsgs
import supybot.ircdb as ircdb
import supybot.schedule as schedule
from random import *
import commands
import re
import time


class Hailo(callbacks.Plugin):
    """Hailo plugin allows your bot to learn and reply
    like human."""

    threaded = True

    magicnick = 'MAGICNICK'

    def __init__(self, irc):
        self.__parent = super(Hailo, self)
        self.__parent.__init__(irc)

    def cmd(self, channel):
        dataDir = conf.supybot.directories.data
        channel = channel.lower()
        chandir = dataDir.dirize(channel)
        dataDir = dataDir.dirize(channel + "/hailo.sqlite")
        return 'hailo -b %s' % dataDir

    def brainstats (self,irc,msg,args):
        if not irc.isChannel(msg.args[0]):
            irc.reply("No brains in private! (each channel have a different brain)")
            return
        out = commands.getoutput('%s %s' % (self.cmd(msg.args[0]),'-s'))
        out = out.replace ('\n',', ')
        irc.reply(out)
    brainstats = wrap(brainstats)
  

    def doPrivmsg(self, irc, msg):
        if callbacks.addressed(irc.nick, msg): #message is direct command
            return
        (channel, text) = msg.args

        if ircmsgs.isAction(msg):
            text = ircmsgs.unAction(msg)

        learn = self.registryValue('learn', channel)
        reply = self.registryValue('reply', channel)
        replyOnMention = self.registryValue('replyOnMention', channel)
        replyWhenSpokenTo = self.registryValue('replyWhenSpokenTo', channel)

        mention = irc.nick.lower() in text.lower()
        spokenTo = msg.args[1].lower().startswith('%s: ' % irc.nick.lower())

        if replyWhenSpokenTo and spokenTo:
            reply = 100
            text = text.replace('%s: ' % irc.nick, '')
            text = text.replace('%s: ' % irc.nick.lower(), '')

        if replyOnMention and mention:
            if not replyWhenSpokenTo and spokenTo:
                reply = 0
            else:
                reply = 100

        if randint(0, 99) < reply:
            self.reply(irc, msg, text)

        if learn:
            self.learn(irc, msg, text)

    def hailo(self, irc, msg, args, message):
        """<message>

        Replies to message using Markov Chain Technology™."""
        channel = msg.args[0]
        if not irc.isChannel(channel):
            irc.error('Not in a channel, not sure what database to use.')
            return

        reply = self.registryValue('reply', channel)
        self.reply(irc, msg, message)
    hailo = wrap(hailo, ['text'])

    def sanitize(self, t):
        b = t
        try:
            t = t.replace('`','')
            t = t.replace('`','')
            t = t.replace('|','')
            t = t.replace('&','')
            t = t.replace('>', '')
            t = t.replace('<', '')
            t = t.replace(';', '')
            t = t.replace('"', '')
            return t
        except:
            self.log.error('Hailo crashed on this message: ' + str(b))
        return

    # Remove nicks when adding to DB.
    def strip_nick(self, irc, msg, text):
        for user in irc.state.channels[msg.args[0]].users:
            text = text.replace(' %s ' % user, ' %s ' % self.magicnick)
            text = text.replace(' %s ' % user.lower(), ' %s ' % self.magicnick)
        return text

    # Add nicks in the channel when getting 'MAGICNICK' from the DB
    def add_nick(self, irc, msg, text):

        # Copy the current users in the channel
        users = []
        for u in irc.state.channels[msg.args[0]].users:
            if irc.nick == u:
                # We don't want the bot talking about itself in third person
                # that is just creepy.
                continue
            users.append(u)

        # If first word is nick, switch with the callers nick.
        if text.startswith(self.magicnick):
            text = text.replace(self.magicnick, msg.nick, 1)
        if text.startswith(self.magicnick.lower()):
            text = text.replace(self.magicnick.lower(), msg.nick, 1)
        if text.startswith(self.magicnick.capitalize()):
            text = text.replace(self.magicnick.capitalize(), msg.nick, 1)
        # Bit of backwards compability.
        if text.startswith('nick'):
            text = text.replace('nick', msg.nick, 1)
        if text.startswith('Nick'):
            text = text.replace('Nick', msg.nick, 1)


        # Get a random user from the given list of users
        randuser = lambda u: u[randint(0, len(u)-1)]

        # For each occurance of magicnick, replace with a random nick.
        # Also check for lowercased versions or capitalize, even though this
        # might finish catch all the occurances before the loop is done
        for i in range(text.lower().count(self.magicnick.lower())):
            text = text.replace(self.magicnick, randuser(users), 1)
            text = text.replace(self.magicnick.lower(), randuser(users), 1)
            text = text.replace(self.magicnick.capitalize(), randuser(users), 1)

        # Do the same with 'nick' (used in older versions of the plugin)
        for i in range(text.lower().count('nick')):
            text = text.replace('nick', randuser(users), 1) # for old DBs
            text = text.replace('Nick', randuser(users), 1) # for old DBs

        for i in range(text.lower().count(irc.nick.lower())):
            text = text.replace(irc.nick, randuser(users), 1) # for old DBs
            text = text.replace(irc.nick.lower(), randuser(users), 1) # for old DBs
            text = text.replace(irc.nick.capitalize(), randuser(users), 1) # for old DBs
        return text

    def learn(self, irc, msg, text):
        if text.startswith(irc.nick):
            self.log.info("Hailo tried to output " + text)
            return
        text = self.sanitize(text)
        text = self.strip_nick(irc, msg, text)
        commands.getoutput('%s %s' % (self.cmd(msg.args[0]), '-l "%s"' % text))

    def reply(self, irc, msg, text):
        nick = msg.nick
        channel = msg.args[0]
        text = self.sanitize(text)
        out = commands.getoutput('%s %s' % (self.cmd(msg.args[0]),'-r "%s"' % text))
        if out and out != text and out != nick and not out.startswith('DBD::SQLite::db'):
            out = out.replace('\n','').replace('\t','')
            out = out.replace(irc.nick, self.magicnick)
            out = self.add_nick(irc, msg, out)
            out = out.strip()
            if out != nick:
                irc.reply(out)
            return
        self.log.warning('Hailo tried to output: "%s"' % str(out))
        
Class = Hailo


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

