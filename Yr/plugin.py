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
import os
import re
import sqlite3
from xml.etree import ElementTree
from bs4 import BeautifulSoup as BS

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
from supybot.commands import *
import supybot.conf as conf
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class Yr(callbacks.Plugin, plugins.ChannelDBHandler):
    """This plugin fetches current information from yr.no (which is a site run by The Norwegian Meteorological Institute)
        for the appropriate location, assuming the correct URL have been set. The language returned is defined by the set URL."""
    threaded = True
    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)
        plugins.ChannelDBHandler.__init__(self)

    """Takes a string. Returns a float or None"""
    def parse_num(self, numstr):
        numstr = numstr.replace(',', '.')
        pattern = r'(-)?\d+(\.\d)?'
        numstr = re.search(pattern, numstr)
        try:
            return float(numstr.group())
        except:
            return
    
    """Takes two floats and returns float or None"""
    def wind_chill(self, temp, wind):
        if not (temp < 10 and (wind*3.6) > 4.8):
            return None

        windchill = 13.12 + 0.6215 * temp- 11.37 * ((wind * 3.6)**0.16) + 0.3965 * temp * ((wind * 3.6)**0.16)
        return windchill

    def temp_format(self, temp, wind, lang):
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
            chill = ' ({0})'.format(chill)
        tempdesc = str(temp) + '°'
        tempdesc = tempdesc.decode('utf8')
        if temp > 0:
            tempdesc = ircutils.mircColor(tempdesc, 'Red').encode('utf8')
        else:
            tempdesc = ircutils.mircColor(tempdesc, 12).encode('utf8')
        if lang != 'en':
            tempdesc = tempdesc.replace('.', ',')
            chill = chill.replace('.', ',')
        return '{0}{1}.'.format(tempdesc, chill)

    def temp(self, irc, msg, args, channel, location):
        """<location>

        Checks first if there are any local aliases added, then if they exist
        in the world db. If language is set to norwegian (bm or nn)
        norwegian db is checked first along with db for postal numbers."""

        if location is None:
            location = self.registryValue('location', channel)

        lang = self.registryValue('lang', channel)
        if lang != 'en' and lang != 'bm' and lang != 'nn':
            irc.reply('Language is not valid. Please fix. Defaulting to english.')
            lang = 'en'

        channel = msg.args[0].lower()
        url = self.getUrl(location, lang)
        if url is None:
            irc.reply("No hits on '%s'." % (location))
            return
        ret = None
        html = self.getHtml(url)
        try:
           ret = self.parseHtml(html, lang)
        except:
            pass
        if ret is None:
            xml = self.getXml(url)
            ret = self.parseXml(xml, lang)
            try:
                pass
            except:
                pass
        if ret is None:
            ret = 'Failed to parse :('
        irc.reply(ret)
        # TODO: Output. Sun. Moon.
    temp = wrap(temp, ['channel', optional('text')])
    
    def getHtml(self, url):
        url = url.replace('/varsel.xml', '')
        url = url.replace('/forecastl.xml', '')
        html = utils.web.getUrl(url)
        return html

    def getXml(self, url):
        xml = utils.web.getUrl(url)
        return xml

    def parseXml(self, xml, lang):
        tree = ElementTree.fromstring(xml)
        location = tree.find('.//location')
        name = location.find('.//name').text
        country = location.find('.//country').text
        loctype = location.find('.//type').text

        forecast = tree.find('.//forecast')[0][0]

        symbol = forecast[0].attrib['name']
        # precipitation = forecast[1].attrib['value']
        windDirection = forecast[2].attrib['name']
        windSpeedName = forecast[3].attrib['name']
        windSpeedValue = forecast[3].attrib['mps']
        temperature = forecast[4].attrib['value']
        pressure = forecast[5].attrib['value']

        temp = self.parse_num(temperature)
        wind = self.parse_num(windSpeedValue)
        if lang != 'en':
            windSpeedValue = str(windSpeedValue).replace('.', ',')

        ret = self.temp_format(temp, wind, lang)
        lang_from = lambda x: 'from' if x == 'en' else 'fra'
        if symbol:
            ret += ' {0}.'.format(symbol.encode('utf8'))
        if wind:
            ret += ' {0}, {1} m/s {2} {3}.'.format(windSpeedName.encode('utf8'),
                    windSpeedValue, lang_from(lang), windDirection.lower().encode('utf8'))
        ret += ' ({0}, {1})'.format(name.encode('utf8'), country.encode('utf8'))
        return ret

    def parseHtml(self, html, lang):
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
            try:
                data = station.tbody.find_all('tr')[1]
            except:
                continue
            desc, temp, wind, winddesc, Name = None, None, None, None, None
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
                winddesc = data.find_all(class_='txt-left')[0].text.strip()
            except:
                pass
            if not temp:
                continue
            temp = self.parse_num(temp)
            wind = self.parse_num(winddesc)
            ret = self.temp_format(temp, wind, lang)
            if desc:
                ret += ' {0}.'.format(desc.encode('utf8'))
            if wind:
                ret += ' {0}.'.format(winddesc.encode('utf8'))
            ret += ' ({0})'.format(name.encode('utf8'))
            return ret

    def getUrl(self, location, lang):
        url = self.getLocalUrl(location, lang)
        if url is not None:
            return url

        if lang == 'bm' or lang == 'nn':
            if len(location) == 4 and location.isdigit():
                url = self.getPostalUrl(location, lang)
            else:
                url = self.getNorgeUrl(location, lang)
        if url is not None:
            return url

        url = self.getWorldUrl(location, lang)
        return url

    def dbQuery(self, query, parameter):
        db = self.getDb('')
        cursor = db.cursor()
        cursor.execute(query, (parameter,))
        results = cursor.fetchall()
        return results

    def getPostalUrl(self, num, lang):
        sql = "SELECT url%s FROM postal WHERE postnr=?" % (lang)
        results = self.dbQuery(sql, num)
        if len(results) != 0:
            return results[0][0]
        return None

    def getNorgeUrl(self, loc, lang):
        sql = "SELECT url%s, priority FROM norge WHERE name = ? COLLATE NOCASE" % (lang)
        results = self.dbQuery(sql, loc)
        if len(results) == 0:
            sql = "SELECT url%s, priority FROM norge WHERE name LIKE ? COLLATE NOCASE" % (lang)
            loc += '%'
            results = self.dbQuery(sql, loc)

        if len(results) != 0:
            results = sorted(results, key=lambda x: x[1], reverse=False)
            return results[0][0]
        return None

    def getWorldUrl(self, loc, lang):
        sql = "SELECT url%s, population FROM world WHERE name%s = ? COLLATE NOCASE" % (lang,
                lang)
        results = self.dbQuery(sql, loc)
        if len(results) == 0:
            sql = "SELECT url%s, population FROM world WHERE name%s LIKE ? COLLATE NOCASE" % (lang,
                    lang)
            loc += '%'
            results = self.dbQuery(sql, loc)
        if len(results) != 0:
            results = sorted(results, key=lambda x: x[1], reverse=True) #TODO: Check way or sorting.
            return results[0][0]
        return None

    def getLocalUrl(self, alias, lang):
        return None

    def filldb(self, irc, msg, args, verification):
        """<yes>
        Loads the files verda.txt, noreg.txt and postnummer.txt into the local
        database.
        """
        path = os.path.dirname(__file__)
        world = os.path.join(path, 'verda.txt')
        norge = os.path.join(path, 'noreg.txt')
        postnr = os.path.join(path, 'postnummer.txt')
        db = self.getDb('')
        cursor = db.cursor()

        cursor.execute("SELECT COUNT(*) FROM norge")
        results = cursor.fetchall()
        if (results[0][0] == 0):
            f = open(norge)
            for line in f.readlines():
                w = line.split('\t')
                cursor.execute("""INSERT INTO norge (kommunenr, name, priority,
                        locationtypenn, locationtypebn, locationtypeen,
                        municipality, county, lat, lon, amsl, urlnn, urlbm, urlen)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (w[0], w[1], w[2], w[3], w[4], w[5], w[6], w[7], w[8], w[9], w[10], w[11], w[12], w[13],))

        cursor.execute("SELECT COUNT(*) FROM world")
        results = cursor.fetchall()
        if (results[0][0] == 0):
            f = open(world)
            for line in f.readlines():
                w = line.split('\t')
                cursor.execute("""INSERT INTO world (countrycode, namenn,
                        namebm, nameen, geonamesid, locationtypenn,
                        locationtypebm, locationtypeen, countrynn, countrybm,
                        countryen, population, lat, lon, amsl, urlnn, urlbm,
                        urlen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?)""", (w[0], w[1], w[2], w[3], w[4],
                            w[5], w[6], w[7], w[8], w[9], w[10], w[11], w[12],
                            w[13], w[14], w[15], w[16], w[17],))

        cursor.execute("SELECT COUNT(*) FROM postal")
        results = cursor.fetchall()
        if (results[0][0] == 0):
            f = open(postnr)
            for line in f.readlines():
                w = line.split('\t')
                cursor.execute("""INSERT INTO postal (postnr, name, type,
                        kommunenr, lat, lon, note, urlnn, urlbm, urlen) VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (w[0], w[1], w[2], w[3], w[4],
                            w[5], w[6], w[7], w[8], w[9],))

        db.commit()

    filldb= wrap(filldb, [('checkCapability', 'owner'), ('literal',
        'yes')])


    def makeDb(self, _):
        # Second argument is not used
        globaldb = conf.supybot.directories.data.dirize('Yr.db')
        if os.path.exists(globaldb):
            db = sqlite3.connect(globaldb)
            db.text_factory = str
            return db
        db = sqlite3.connect(globaldb)
        db.text_factory = str
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE norge (
                          id INTEGER PRIMARY KEY,
                          kommunenr INTEGER,
                          name TEXT,
                          priority INTEGER,
                          locationtypenn TEXT,
                          locationtypebn TEXT,
                          locationtypeen TEXT,
                          municipality TEXT,
                          county TEXT,
                          lat TEXT,
                          lon TEXT,
                          amsl TEXT,
                          urlnn TEXT,
                          urlbm TEXT,
                          urlen TEXT
                          )""")
        cursor.execute("""CREATE TABLE world (
                          id INTEGER PRIMARY KEY,
                          countrycode TEXT,
                          namenn TEXT,
                          namebm TEXT,
                          nameen TEXT,
                          geonamesid TEXT,
                          locationtypenn TEXT,
                          locationtypebm TEXT,
                          locationtypeen TEXT,
                          countrynn TEXT,
                          countrybm TEXT,
                          countryen TEXT,
                          population INTEGER,
                          lat TEXT,
                          lon TEXT,
                          amsl TEXT,
                          urlnn TEXT,
                          urlbm TEXT,
                          urlen TEXT
                          )""")
        cursor.execute("""CREATE TABLE postal (
                          id INTEGER PRIMARY KEY,
                          postnr TEXT,
                          name TEXT,
                          type TEXT,
                          kommunenr INTEGER,
                          lat TEXT,
                          lon TEXT,
                          note TEXT,
                          urlnn TEXT,
                          urlbm TEXT,
                          urlen TEXT
                          )""")
        cursor.execute("""CREATE TABLE local (
                          id INTEGER PRIMARY KEY,
                          alias TEXT,
                          url TEXT,
                          channel TEXT
                          )""")
        db.commit()
        return db


Class = Yr
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
