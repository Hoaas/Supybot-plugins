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
from bs4 import BeautifulSoup as BS

import supybot.utils as utils
from supybot.commands import *
import supybot.conf as conf
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class Yr(callbacks.Plugin):
    """This plugin fetches current information from yr.no (which is a site run by The Norwegian Meteorological Institute)
        for the appropriate location, assuming the correct URL have been set. The language returned is defined by the set URL."""
    threaded = True

    def parse_num(self, numstr):
        numstr = numstr.encode('utf8')
        numstr = numstr.replace('°', '')
        numstr = numstr.replace(',', '.')
        try:
            num = float(numstr)
        except:
            return
        return num

    def parse_wind(self, windstr):
        pattern = r'\d+([,|.]\d)?'
        wind = re.search(pattern, windstr)
        if wind:
            wind = self.parse_num(wind.group())
            return wind


    def wind_chill(self, temp, wind):
        if not temp or not wind:
            return None
        temp = self.parse_num(temp)
        wind = self.parse_wind(wind)
        if not (temp < 10 and (wind*3.6) > 4.8):
            return None

        windchill = 13.12 + 0.6215 * temp- 11.37 * ((wind * 3.6)**0.16) + 0.3965 * temp * ((wind * 3.6)**0.16)
        return windchill

    def temp_format(self, temp, wind):
        chill = ''
        windchill = None
        if wind:
            windchill = self.wind_chill(temp, wind)
        if windchill is not None:
            chill = '{0:.1f}°'.format(windchill)
            if windchill > 0:
                chill = ircutils.mircColor(str(chill), 'Red')
            else:
                chill = ircutils.mircColor(str(chill), 12)
            if ',' in temp:
                chill = chill.replace('.', ',')
            chill = ' ({0})'.format(chill)

        if self.parse_num(temp) > 0:
            temp = ircutils.mircColor(temp, 'Red').encode('utf8')
        else:
            temp = ircutils.mircColor(temp, 12).encode('utf8')
        return '{0}{1}.'.format(temp, chill)

    def temp(self, irc, msg, args, boop):
        """

        boop."""
        url = 'http://www.yr.no/sted/Norge/S%C3%B8r-Tr%C3%B8ndelag/Trondheim/Trondheim/'
        if boop is None:
            pass
        elif boop.lower() == 'oslo':
            url = 'http://www.yr.no/sted/Norge/Oslo/Oslo/Oslo/'
        elif boop.lower() == 'kongsberg':
            url = 'http://www.yr.no/sted/Norge/Buskerud/Kongsberg/Kongsberg/'
        elif boop.lower() == 'trondheim':
            pass
        else:
            irc.reply('Boop. Sorry. Bare Trondheim, Oslo og Kongsberg atm. :(:( Fix kommer senere!')
            return
        html = utils.web.getUrl(url)
        soup = BS(html)
        body = soup.body
        stations = body.find_all(
            class_='yr-page')[0].find_all(
            class_='yr-content')[0].find_all(
            class_='yr-content-body')[0].find_all(
            class_='yr-content-body yr-top-margin yr-content-stickynav clearfix')[0].find_all(
            class_='yr-content-stickynav-three-fifths left')[0].find_all(
            class_='yr-content-stickynav-three-fifths yr-stations left clear')[0].find_all(
            class_='yr-table yr-table-station yr-popup-area')
        for station in stations:
            data = station.tbody.find_all('tr')[1]
            desc, temp, wind, Name = None, None, None, None
            try:
                name = station.thead.tr.th.strong.text
                desc = data.td.img.get('alt')
            except:
                pass
            try:
                temp = data.find_all(class_='temperature')[0].text
            except:
                pass
            try:
                wind = data.find_all(class_='txt-left')[0].text.strip()
            except:
                pass
            if not temp:
                continue
            ret = self.temp_format(temp, wind)
            if desc:
                ret += ' {0}.'.format(desc.encode('utf8'))
            if wind:
                ret += ' {0}.'.format(wind.encode('utf8'))
            ret += ' ({0})'.format(name.encode('utf8'))
            irc.reply(ret)
            return
            # TODO: Output. Get url from database. Sun. Moon.
            # Non-norwegian places.
    temp = wrap(temp, [optional('text')])
    
Class = Yr


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
