###
# Copyright (c) 2014, Terje Hoås
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
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('BattleNet')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

class BattleNet(callbacks.Plugin):
    """Add the help for "@plugin help BattleNet" here
    This should describe *how* to use this plugin."""
    threaded = True

    hosts = {
        'US' : 'us.battle.net',
        'Europe' : 'eu.battle.net',
        'Korea' : 'kr.battle.net',
        'Taiwan' : 'tw.battle.net',
        'China' : 'www.battlenet.com.cn'
    }

    def wow(self, irc, msg, args, server):
        """[server] [server2] [server3] ...
        World of Warcraft server status. Without a server name an overview of
        the server status will be given."""
        channel = msg.args[0].lower()
        region = self.registryValue('region', channel)
        host = self.hosts[region]

        api = '/api/wow/realm/status'
        url = 'http://' + host + api
        if len(server) != 0:
            url += '?realms='
            url += ','.join(server)
        data = utils.web.getUrl(url).decode()
        try:
            data = json.loads(data)
        except:
            data = utils.web.getUrl(url).decode()
            data = json.loads(data)

        realms = data.get('realms')

        if len(server) != 0 and len(realms) > 5:
            irc.error('Too many servers. Either you added over 5, or you did not type in a server name.')
            return
        if len(realms) == 0:
            irc.error('No servers found! Blizzard API might be broken!')

        if len(server) == 0:
            # General status
            queue = 0
            count = {
                     'population' : {},
                     'realm_type' : {},
                     'tb-faction' : {},
                     'wg-faction' : {}
            }
            total_realms = len(realms)
            for realm in realms:
                if (realm.get('queue')):
                    queue += 1
                rtype = realm.get('type')
                popsize = realm.get('population')
                tb = self.get_faction(realm.get('tol-barad').get('controlling-faction'))
                wg = self.get_faction(realm.get('wintergrasp').get('controlling-faction'))

                if not count.get('population').get(popsize):
                    count.get('population')[popsize] = 0
                #if not count.get('realm_type').get(rtype):
                #    count.get('realm_type')[rtype] = 0
                if not count.get('tb-faction').get(tb):
                    count.get('tb-faction')[tb] = 0
                if not count.get('wg-faction').get(wg):
                    count.get('wg-faction')[wg] = 0
                count.get('population')[popsize] += 1
                #count.get('realm_type')[rtype] += 1
                count.get('tb-faction')[tb] += 1
                count.get('wg-faction')[wg] += 1
            pops = []
            for key in count.get('population').keys():
                pops.append('{0}: {1}'.format(key, count.get('population')[key]))
            tb_num = []
            for key in count.get('tb-faction').keys():
                tb_num.append('{0}: {1}'.format(key, count.get('tb-faction')[key]))
            wg_num = []
            for key in count.get('wg-faction').keys():
                wg_num.append('{0}: {1}'.format(key, count.get('wg-faction')[key]))

            irc.reply('{0} realms ({5}). Queue on {1}. Numbers of servers with population {2}. Tol Barad: {3}. Wintergrasp: {4}.'.format(total_realms, queue, ', '.join(pops), ', '.join(tb_num), ', '.join(wg_num), region))
        else:
            # Status for each realm
            for realm in realms:
                name = realm.get('name')
                pop = realm.get('population')
                queue = realm.get('queue')
                locale = realm.get('locale')
                timezone = realm.get('timezone')
                status = realm.get('status')

                # PvP
                tb = realm.get('tol-barad')
                tb_curr = self.get_faction(tb.get('controlling-faction'))
                tb_status = self.get_status_text(tb.get('status'))
                tb_next = tb.get('next')

                wg = realm.get('tol-barad')
                wg_curr = self.get_faction(wg.get('controlling-faction'))
                wg_status = self.get_status_text(wg.get('status'))
                wg_next = wg.get('next')
                
                irc.reply('{0} - {1}. Queue: {2}. Population: {3}. TB Status: {6}, {4} controlled. WG: {7}, {5} controlled.'.format(name, self.get_up_down(status), self.get_queue_text(queue), pop, tb_curr, wg_curr, tb_status, wg_status))
    wow = wrap(wow, [any('anything')])

    def get_faction(self, faction):
        if faction == 0:
            faction = 'Horde'
        elif faction == 1:
            faction = 'Alliance'
        else:
            faction = 'Unknown faction'
        return faction

    def get_status_text(self, status):
        if status == -1:
            status = 'Unknown'
        elif status == 0:
            status = 'Idle'
        elif status == 1:
            status = 'Populating'
        elif status == 2:
            status = 'Active'
        elif status == 3:
            status = 'Concluded'
        return status

    def get_up_down(self, status):
        if status:
            return 'Up'
        else:
            return 'Down'
    def get_queue_text(self, queue):
        if queue:
            return 'Yes'
        else:
            return 'No'

Class = BattleNet
