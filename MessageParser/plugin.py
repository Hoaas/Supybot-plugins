###
# Copyright (c) 2010, Daniel Folkinshteyn
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

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import supybot.conf as conf
import supybot.ircdb as ircdb

import re
import os
import time

#try:
    #import sqlite
#except ImportError:
    #raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           #'plugin.  Download it at ' \
                           #'<http://code.google.com/p/pysqlite/>'

try:
    import sqlite3
except ImportError:
    from pysqlite2 import dbapi2 as sqlite3 # for python2.4

# these are needed cuz we are overriding getdb
import threading
import supybot.world as world


import supybot.log as log


class MessageParser(callbacks.Plugin, plugins.ChannelDBHandler):
    """This plugin can set regexp triggers to activate the bot.
    Use 'add' command to add regexp trigger, 'remove' to remove."""
    threaded = True
    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)
        plugins.ChannelDBHandler.__init__(self)
    
    def makeDb(self, filename):
        """Create the database and connect to it."""
        if os.path.exists(filename):
            db = sqlite3.connect(filename)
            db.text_factory = str
            return db
        db = sqlite3.connect(filename)
        db.text_factory = str
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE triggers (
                          id INTEGER PRIMARY KEY,
                          regexp TEXT UNIQUE ON CONFLICT REPLACE,
                          added_by TEXT,
                          added_at TIMESTAMP,
                          usage_count INTEGER,
                          action TEXT,
                          locked BOOLEAN
                          )""")
        db.commit()
        return db
    
    # override this because sqlite3 doesn't have autocommit
    # use isolation_level instead.
    def getDb(self, channel):
        """Use this to get a database for a specific channel."""
        currentThread = threading.currentThread()
        if channel not in self.dbCache and currentThread == world.mainThread:
            self.dbCache[channel] = self.makeDb(self.makeFilename(channel))
        if currentThread != world.mainThread:
            db = self.makeDb(self.makeFilename(channel))
        else:
            db = self.dbCache[channel]
        db.isolation_level = None
        return db
    
    def _updateRank(self, channel, regexp):
        if self.registryValue('keepRankInfo', channel):
            db = self.getDb(channel)
            cursor = db.cursor()
            cursor.execute("""SELECT usage_count
                      FROM triggers
                      WHERE regexp=?""", (regexp,))
            old_count = cursor.fetchall()[0][0]
            cursor.execute("UPDATE triggers SET usage_count=? WHERE regexp=?", (old_count + 1, regexp,))
            db.commit()
    
    def _runCommandFunction(self, irc, msg, command):
        """Run a command from message, as if command was sent over IRC."""
        tokens = callbacks.tokenize(command)        
        try:
            self.Proxy(irc.irc, msg, tokens)
        except Exception, e:
            log.exception('Uncaught exception in function called by MessageParser:')
    
    def _checkManageCapabilities(self, irc, msg, channel):
        """Check if the user has any of the required capabilities to manage
        the regexp database."""
        capabilities = self.registryValue('requireManageCapability')
        if capabilities:
            for capability in re.split(r'\s*;\s*', capabilities):
                if capability.startswith('channel,'):
                    capability = ircdb.makeChannelCapability(channel, capability[8:])
                if capability and ircdb.checkCapability(msg.prefix, capability):
                    #print "has capability:", capability
                    return True
            return False
        else:
            return True
        
    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        if not irc.isChannel(channel):
            return
        if self.registryValue('enable', channel):
            if callbacks.addressed(irc.nick, msg): #message is direct command
                return
            actions = []
            db = self.getDb(channel)
            cursor = db.cursor()
            cursor.execute("SELECT regexp, action FROM triggers")
            results = cursor.fetchall()
            if len(results) == 0:
                return
            for (regexp, action) in results:
                for match in re.finditer(regexp, msg.args[1]):
                    if match is not None:
                        thisaction = action
                        self._updateRank(channel, regexp)
                        for (i, j) in enumerate(match.groups()):
                            thisaction = re.sub(r'\$' + str(i+1), match.group(i+1), thisaction)
                        actions.append(thisaction)
            
            for action in actions:
                self._runCommandFunction(irc, msg, action)
    
    def add(self, irc, msg, args, channel, regexp, action):
        """[<channel>] <regexp> <action>

        Associates <regexp> with <action>.  <channel> is only
        necessary if the message isn't sent on the channel
        itself.  Action is echoed upon regexp match, with variables $1, $2, 
        etc. being interpolated from the regexp match groups."""
        if not self._checkManageCapabilities(irc, msg, channel):
            capabilities = self.registryValue('requireManageCapability')
            irc.errorNoCapability(capabilities, Raise=True)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT id, usage_count, locked FROM triggers WHERE regexp=?", (regexp,))
        results = cursor.fetchall()
        if len(results) != 0:
            (id, usage_count, locked) = map(int, results[0])
        else:
            locked = 0
            usage_count = 0
        if not locked:
            try:
                re.compile(regexp)
            except Exception, e:
                irc.error('Invalid python regexp: %s' % (e,))
                return
            if ircdb.users.hasUser(msg.prefix):
                name = ircdb.users.getUser(msg.prefix).name
            else:
                name = msg.nick
            cursor.execute("""INSERT INTO triggers VALUES
                              (NULL, ?, ?, ?, ?, ?, ?)""",
                            (regexp, name, int(time.time()), usage_count, action, locked,))
            db.commit()
            irc.replySuccess()
        else:
            irc.error('That trigger is locked.')
            return
    add = wrap(add, ['channel', 'something', 'something'])
    
    def remove(self, irc, msg, args, channel, optlist, regexp):
        """[<channel>] [--id] <regexp>]

        Removes the trigger for <regexp> from the triggers database.  
        <channel> is only necessary if
        the message isn't sent in the channel itself.
        If option --id specified, will retrieve by regexp id, not content.
        """
        if not self._checkManageCapabilities(irc, msg, channel):
            capabilities = self.registryValue('requireManageCapability')
            irc.errorNoCapability(capabilities, Raise=True)
        db = self.getDb(channel)
        cursor = db.cursor()
        target = 'regexp'
        for (option, arg) in optlist:
            if option == 'id':
                target = 'id'
        sql = "SELECT id, locked FROM triggers WHERE %s=?" % (target,)
        cursor.execute(sql, (regexp,))
        results = cursor.fetchall()
        if len(results) != 0:
            (id, locked) = map(int, results[0])
        else:
            irc.error('There is no such regexp trigger.')
            return
        
        if locked:
            irc.error('This regexp trigger is locked.')
            return
        
        cursor.execute("""DELETE FROM triggers WHERE id=?""", (id,))
        db.commit()
        irc.replySuccess()
    remove = wrap(remove, ['channel',
                            getopts({'id': '',}),
                            'something'])

    def lock(self, irc, msg, args, channel, regexp):
        """[<channel>] <regexp>

        Locks the <regexp> so that it cannot be
        removed or overwritten to.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        if not self._checkManageCapabilities(irc, msg, channel):
            capabilities = self.registryValue('requireManageCapability')
            irc.errorNoCapability(capabilities, Raise=True)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT id FROM triggers WHERE regexp=?", (regexp,))
        results = cursor.fetchall()
        if len(results) == 0:
            irc.error('There is no such regexp trigger.')
            return
        cursor.execute("UPDATE triggers SET locked=1 WHERE regexp=?", (regexp,))
        db.commit()
        irc.replySuccess()
    lock = wrap(lock, ['channel', 'text'])

    def unlock(self, irc, msg, args, channel, regexp):
        """[<channel>] <regexp>

        Unlocks the entry associated with <regexp> so that it can be
        removed or overwritten.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        if not self._checkManageCapabilities(irc, msg, channel):
            capabilities = self.registryValue('requireManageCapability')
            irc.errorNoCapability(capabilities, Raise=True)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT id FROM triggers WHERE regexp=?", (regexp,))
        results = cursor.fetchall()
        if len(results) == 0:
            irc.error('There is no such regexp trigger.')
            return
        cursor.execute("UPDATE triggers SET locked=0 WHERE regexp=?", (regexp,))
        db.commit()
        irc.replySuccess()
    unlock = wrap(unlock, ['channel', 'text'])

    def show(self, irc, msg, args, channel, optlist, regexp):
        """[<channel>] [--id] <regexp>

        Looks up the value of <regexp> in the triggers database.
        <channel> is only necessary if the message isn't sent in the channel 
        itself.
        If option --id specified, will retrieve by regexp id, not content.
        """
        db = self.getDb(channel)
        cursor = db.cursor()
        target = 'regexp'
        for (option, arg) in optlist:
            if option == 'id':
                target = 'id'
        sql = "SELECT regexp, action FROM triggers WHERE %s=?" % (target,)
        cursor.execute(sql, (regexp,))
        results = cursor.fetchall()
        if len(results) != 0:
            (regexp, action) = results[0]
        else:
            irc.error('There is no such regexp trigger.')
            return
            
        irc.reply("The action for regexp trigger \"%s\" is \"%s\"" % (regexp, action))
    show = wrap(show, ['channel', 
                        getopts({'id': '',}),
                        'something'])

    def info(self, irc, msg, args, channel, optlist, regexp):
        """[<channel>] [--id] <regexp>

        Display information about <regexp> in the triggers database.
        <channel> is only necessary if the message isn't sent in the channel 
        itself.
        If option --id specified, will retrieve by regexp id, not content.
        """
        db = self.getDb(channel)
        cursor = db.cursor()
        target = 'regexp'
        for (option, arg) in optlist:
            if option == 'id':
                target = 'id'
        sql = "SELECT * FROM triggers WHERE %s=?" % (target,)
        cursor.execute(sql, (regexp,))
        results = cursor.fetchall()
        if len(results) != 0:
            (id, regexp, added_by, added_at, usage_count, 
                    action, locked) = results[0]
        else:
            irc.error('There is no such regexp trigger.')
            return
            
        irc.reply("The regexp id is %d, regexp is \"%s\", and action is"
                    " \"%s\". It was added by user %s on %s, has been "
                    "triggered %d times, and is %s." % (id, 
                    regexp, 
                    action,
                    added_by,
                    time.strftime(conf.supybot.reply.format.time(),
                                     time.localtime(int(added_at))),
                    usage_count,
                    locked and "locked" or "not locked",))
    info = wrap(info, ['channel', 
                        getopts({'id': '',}),
                        'something'])

    def list(self, irc, msg, args, channel):
        """[<channel>]

        Lists regexps present in the triggers database.
        <channel> is only necessary if the message isn't sent in the channel 
        itself. Regexp ID listed in paretheses.
        """
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT regexp, id FROM triggers")
        results = cursor.fetchall()
        if len(results) != 0:
            regexps = results
        else:
            irc.reply('There are no regexp triggers in the database.')
            return
        
        s = [ "\"%s\" (%d)" % (regexp[0], regexp[1]) for regexp in regexps ]
        separator = self.registryValue('listSeparator', channel)
        irc.reply(separator.join(s))
    list = wrap(list, ['channel'])

    def rank(self, irc, msg, args, channel):
        """[<channel>]
        
        Returns a list of top-ranked regexps, sorted by usage count 
        (rank). The number of regexps returned is set by the 
        rankListLength registry value. <channel> is only necessary if the 
        message isn't sent in the channel itself.
        """
        numregexps = self.registryValue('rankListLength', channel)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT regexp, usage_count
                          FROM triggers
                          ORDER BY usage_count DESC
                          LIMIT ?""", (numregexps,))
        regexps = cursor.fetchall()
        if len(regexps) == 0:
            irc.reply('There are no regexp triggers in the database.')
            return
        s = [ "#%d \"%s\" (%d)" % (i+1, regexp[0], regexp[1]) for i, regexp in enumerate(regexps) ]
        irc.reply(", ".join(s))
    rank = wrap(rank, ['channel'])

    def vacuum(self, irc, msg, args, channel):
        """[<channel>]
        
        Vacuums the database for <channel>.
        See SQLite vacuum doc here: http://www.sqlite.org/lang_vacuum.html
        <channel> is only necessary if the message isn't sent in 
        the channel itself.
        First check if user has the required capability specified in plugin 
        config requireVacuumCapability.
        """
        capability = self.registryValue('requireVacuumCapability')
        if capability:
            if not ircdb.checkCapability(msg.prefix, capability):
                irc.errorNoCapability(capability, Raise=True)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""VACUUM""")
        db.commit()
        irc.replySuccess()
    vacuum = wrap(vacuum, ['channel'])

Class = MessageParser


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
