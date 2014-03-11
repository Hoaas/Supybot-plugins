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
import time
import sqlite3
import urllib
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
        if not numstr:
            return
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
        if temp > 0:
            tempdesc = ircutils.mircColor(tempdesc, 'Red')
        else:
            tempdesc = ircutils.mircColor(tempdesc, 12)
        if lang != 'en':
            tempdesc = tempdesc.replace('.', ',')
            chill = chill.replace('.', ',')
        return '{0}{1}.'.format(tempdesc, chill)

    def temp(self, irc, msg, args, channel, location):
        """[#channel] <location>

        Checks first if there are any local aliases added, then if they exist
        in the world db. If language is set to norwegian (bm or nn)
        norwegian db is checked first along with db for postal numbers."""

        lang = self.registryValue('lang', channel)
        if lang != 'en' and lang != 'bm' and lang != 'nn':
            irc.reply('Language is not valid. Please fix. Defaulting to english.')
            lang = 'en'
        channel = msg.args[0].lower()
        url = self.getUrl(location, lang, channel, msg.nick)
        if url is None:
            if location is None:
                 location = self.registryValue('location', channel)
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
            try:
                ret = self.parseXml(xml, lang)
            except:
                pass
        if ret is None:
            ret = 'Failed to parse :('
        irc.reply(ret)
    temp = wrap(temp, ['channel', optional('text')])

    def sun(self, irc, msg, args, channel, location):
        """<location>

        Checks first if there are any local aliases added, then if they exist
        in the world db. If language is set to norwegian (bm or nn)
        norwegian db is checked first along with db for postal numbers."""
        lang = self.registryValue('lang', channel)
        if lang != 'en' and lang != 'bm' and lang != 'nn':
            irc.reply('Language is not valid. Please fix. Defaulting to english.')
            lang = 'en'
        channel = msg.args[0].lower()
        url = self.getUrl(location, lang, channel, msg.nick)
        if url is None:
            if location is None:
                 location = self.registryValue('location', channel)
            irc.reply("No hits on '%s'." % (location))
            return
        xml = self.getXml(url)
        ret = self.parseXmlSun(xml, lang)
        irc.reply(ret)
    sun = wrap(sun, ['channel', optional('text')])
    
    def getHtml(self, url):
        url = url.replace('/varsel.xml', '')
        url = url.replace('/forecast.xml', '')
        html = utils.web.getUrl(url).decode()
        return html

    def getXml(self, url):
        xml = utils.web.getUrl(url).decode()
        return xml

    def parseXmlSun(self, xml, lang):
        tree = ElementTree.fromstring(xml)
        location = tree.find('.//location')
        name = location.find('.//name').text
        country = location.find('.//country').text
        loctype = location.find('.//type').text

        sunriseLoc = 'Sunrise'
        sunsetLoc = 'Sunset'
        if lang == 'bm' or lang == 'nn':
            sunriseLoc = 'Soloppgang'
            sunsetLoc = 'Solnedgang'

        sun = tree.find('.//sun')
        if sun.get('never_rise'):
            if lang == 'bm' or lang == 'nn':
                return 'Mørketid.'
            else:
                return 'Polar night.'
        if sun.get('never_set'):
            if lang == 'bm' or lang == 'nn':
                return 'Midnattsol.'
            else:
                return 'Midnight sun.'
        sunrise = sun.attrib['rise']
        sunset = sun.attrib['set']

        sunrise = time.strptime(sunrise, '%Y-%m-%dT%H:%M:%S')
        sunset = time.strptime(sunset, '%Y-%m-%dT%H:%M:%S')

        sunrise = time.strftime('%H:%M', sunrise)
        sunset = time.strftime('%H:%M', sunset)
    
        ret = '{0} {2}. {1} {3}'.format(sunriseLoc, sunsetLoc, sunrise, sunset)
        ret += ' ({0}, {1})'.format(name, country)
        return ret

    def parseXml(self, xml, lang):
        tree = ElementTree.fromstring(xml)
        location = tree.find('.//location')
        name = location.find('.//name').text
        country = location.find('.//country').text
        loctype = location.find('.//type').text

        forecast = tree.find('.//forecast').find('.//tabular').find('.//time')
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
            ret += ' {0}.'.format(symbol)
        if wind:
            ret += ' {0}, {1} m/s {2} {3}.'.format(windSpeedName,
                    windSpeedValue, lang_from(lang), windDirection.lower())
        ret += ' ({0}, {1})'.format(name, country)
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
                ret += ' {0}.'.format(desc)
            if wind:
                ret += ' {0}.'.format(winddesc)
            ret += ' ({0})'.format(name)
            return ret

    def hotncold(self, irc, msg, args):
        """takes no arguments
        Hottest, coldest and wettest place in Norway the last day. Hours between 08 and 20 are counted. Updated around 2100 every day. Before that temperature for the previous day is shown."""
        lang = 'bm'

        url = 'http://www.yr.no/observasjonar/statistikk.html'
        html = utils.web.getUrl(url)
        soup = BS(html)
        tbody = soup.body.find_all(class_='yr-content-stickynav-half left')
        tr = tbody[0].findAll('tr')
        toprow = tr[1]

        hottestName = toprow.findAll('td')[0].text.strip()
        hottestTemp = toprow.findAll('td')[1].text.strip()
        hottestTemp = self.parse_num(hottestTemp)
        hottestTemp = self.temp_format(hottestTemp, None, lang)

        coldestName = toprow.findAll('td')[2].text.strip()
        coldestTemp = toprow.findAll('td')[3].text.strip()
        coldestTemp = self.parse_num(coldestTemp)
        coldestTemp = self.temp_format(coldestTemp, None, lang)

        wettestName = toprow.findAll('td')[4].text.strip()
        wettestAmount = toprow.findAll('td')[5].text.strip().replace('\n', '')

        ret = 'Varmest: {0} {1} Kaldest: {2} {3} Våtest: {4} {5}.'.format(hottestName, hottestTemp, coldestName, coldestTemp, wettestName, wettestAmount)
        irc.reply(ret)
    hotncold = wrap(hotncold)


    def _pollen(self, locations, loc):
        # locations is the dictionary, loc is the integer
        url = "http://www.yr.no/pollen/"
        
        plants = {0: "Or",
            1: "Hassel",
            2: "Salix",
            3: "Bjørk",
            4: "Gress",
            5: "Burot"
        }
        
        html = utils.web.getUrl(url).decode()

        first = locations[loc]
        # Dropping everything before our first find
        html = html[html.find(first):]
        html = html[:html.find('</tr>')]
        name = html[:html.find('<')]
        
        html = html[html.find('<td'):]
        html = html.splitlines()
        
        plantcounter = 0
        today = {}
        tomorrow = {}
        for i in range(len(html)):
            if ((i % 2) == 0):
                if(html[i].find('class') != -1):
                    today[plantcounter] = html[i][html[i].find('title="')+7:html[i].find('" />')]
            else:
                if(html[i].find('class') != -1):
                    tomorrow[plantcounter] = html[i][html[i].find('title="')+7:html[i].find('" />')]
                plantcounter += 1
        rtoday = ""
        rtomorrow = ""
        for i in today:
            if "Beskjeden" in today[i]:
                today[i] = ircutils.mircColor(today[i], "Light green")
            elif "Moderat" in today[i]:
                today[i] = ircutils.mircColor(today[i], "Orange")
            elif "Kraftig" in today[i]:
                today[i] = ircutils.mircColor(today[i], "Red")
            elif "Ekstrem" in today[i]:
                today[i] = ircutils.mircColor(today[i], "Brown")

            rtoday += plants[i] + " (" + today[i] + "), "
        for i in tomorrow:
            if "Beskjeden" in tomorrow[i]:
                tomorrow[i] = ircutils.mircColor(tomorrow[i], "Light green")
            elif "Moderat" in tomorrow[i]:
                tomorrow[i] = ircutils.mircColor(tomorrow[i], "Orange")
            elif "Kraftig" in tomorrow[i]:
                tomorrow[i] = ircutils.mircColor(tomorrow[i], "Red")
            elif "Ekstrem" in tomorrow[i]:
                tomorrow[i] = ircutils.mircColor(tomorrow[i], "Brown")
            rtomorrow += plants[i] + " (" + tomorrow[i] + "), "
        rtoday = rtoday[:-2]
        rtomorrow = rtomorrow[:-2]
        if (len(rtoday) < 5):
            rtoday = ircutils.bold("I dag") + ": Clear! "
        else:
            rtoday = ircutils.bold("I dag") + ": " + rtoday + ". "
        if (len(rtomorrow) < 5):
            rtomorrow = ircutils.bold("I morgen") + ": Clear!"
        else:
            rtomorrow = ircutils.bold("I morgen") + ": " + rtomorrow + "."
        
        if not rtoday and not rtomorrow:
            return "Ingen pollen varslet."
        if not rtoday:
            return rtomorrow
        if not rtomorrow:
            return rtoday
        return locations[loc] + ": " + rtoday + rtomorrow
        
    def pollen(self, irc, msg, args, loc):
        """[<location>]
        Norwegian only. See "pollen list" for list of locations.
        """
        
        if (loc == "list"):
            irc.reply("1 Østlandet med Oslo, 2 Sørlandet, 3 Rogaland, 4 Hordaland, \
5 Sogn og Fjordane, 6 Møre og Romsdal, 7 Sentrale fjellstrøk i Sør-Norge, 8 Indre Østlandet, \
9 Trøndelag, 10 Nordland, 11 Troms, 12 Finnmark")
            return
        
        # Dictionary with locations
        locations = {1: "Østlandet med Oslo",
                2: "Sørlandet",
                3: "Rogaland",
                4: "Hordaland",
                5: "Sogn og Fjordane",
                6: "Møre og Romsdal",
                7: "Sentrale fjellstrøk i Sør-Norge",
                8: "Indre Østlandet",
                9: "Trøndelag",
                10: "Nordland",
                11: "Troms",
                12: "Finnmark"}
        if not loc:
            loc = self.registryValue('pollen', msg.args[0]) # Default value is 1.

        fail = False
        try:
            loc = int(loc)
            # If the parsing fails we jump to the except.
        # if location is not an integer
        except:
            for l in locations:
                # If we have location that containt the string
                # Using lower() to ignore case.
                if(locations[l].lower().find(loc.lower()) != -1):
                    loc = l
                    fail = False
                    break
                else:
                    fail = True
            # If we have gone through the loop and loc still isn't an integer the location is not found
        
        # If number is outside the accepted range.
        if(not fail and (loc < 1 or loc > 12)):
            fail = True
        if fail:
            irc.reply('Sorry, ' + str(loc) + ' is not a valid location. Check "pollen list" for list of locations.')
            return
        # At this point loc is an integer from 1 to 12
        retstr = self._pollen(locations, loc)
        if (retstr == -1):
            irc.reply('Sorry, failed to retrieve pollentriks.')
        else:
            irc.reply(retstr)
    pollen = wrap(pollen, [additional('text')]) 

    def getUrl(self, location, lang, channel, nick):
        locSet = True
        if location is None:
            location = self.registryValue('location', channel)
            locSet = False
        url = self.getLocalUrl(location, locSet, channel, nick)
        if url is None:
            if lang == 'bm' or lang == 'nn':
                if len(location) == 4 and location.isdigit():
                    url = self.getPostalUrl(location, lang)
                else:
                    url = self.getNorgeUrl(location, lang)
        if url is None:
            url = self.getWorldUrl(location, lang)
        if url is None:
            return None
        # If urlencoding not found, do urlencoding
        if(url.find('%') == -1):
            o = urllib.parse.urlparse(url)
            url = o.scheme + '://' + o.netloc + urllib.parse.quote(o.path)
        url = url.replace('%0D%0A', '') # \r\n-problem. TODO: Proper fix.
        return url

    def dbQuery(self, query, parameter):
        db = self.getDb('')
        cursor = db.cursor()
        cursor.execute(query, parameter)
        results = cursor.fetchall()
        return results

    def getPostalUrl(self, num, lang):
        sql = "SELECT url%s FROM postal WHERE postnr=?" % (lang)
        results = self.dbQuery(sql, (num,))
        if len(results) != 0:
            return results[0][0]
        return None

    def getNorgeUrl(self, loc, lang):
        sql = "SELECT url%s, priority FROM norge WHERE name = ? COLLATE NOCASE" % (lang)
        results = self.dbQuery(sql, (loc,))
        if len(results) == 0:
            sql = "SELECT url%s, priority FROM norge WHERE name LIKE ? COLLATE NOCASE" % (lang)
            loc += '%'
            results = self.dbQuery(sql, (loc,))

        if len(results) != 0:
            results = sorted(results, key=lambda x: x[1], reverse=False)
            return results[0][0]
        return None

    def getWorldUrl(self, loc, lang):
        sql = "SELECT url%s, population FROM world WHERE name%s = ? COLLATE NOCASE" % (lang,
                lang)
        results = self.dbQuery(sql, (loc,))
        if len(results) == 0:
            sql = "SELECT url%s, population FROM world WHERE name%s LIKE ? COLLATE NOCASE" % (lang,
                    lang)
            loc += '%'
            results = self.dbQuery(sql, (loc,))
        if len(results) != 0:
            results = sorted(results, key=lambda x: x[1], reverse=True)
            return results[0][0]
        return None

    def getLocalUrl(self, alias, locSet, channel, nick):
        sql = 'SELECT url FROM local WHERE '
        # sql += 'channel = ?
        if not locSet:
            sql += 'alias = ?'
            results = self.dbQuery(sql, (nick,))
        else:
            # sql += 'channel = ? AND '
            sql += 'alias LIKE ? COLLATE NOCASE'
            results = self.dbQuery(sql, (alias,))
        if len(results) != 0:
            return results[0][0]
        return None

    def addurl(self, irc, msg, args, alias, url):
        """<alias> <yr.no url to location>
        Adds the url to the database so that you can use the alias as a
        location name. If the alias is 'nick' the url will be the default for
        your nick.
        """
        if alias == 'nick':
            alias = msg.nick
        if url[-4:] != '.xml':
            if url[-1:] != '/':
                url += '/'
            url += 'forecast.xml'

        db = self.getDb('')
        cursor = db.cursor()

        cursor.execute("""BEGIN""")
        cursor.execute("""INSERT OR REPLACE INTO local (alias, url, channel)
                VALUES (?, ?, ?)""", (alias, url, msg.args[0]))
        cursor.execute("""COMMIT""")
        irc.reply('Done. URL added for ' + alias + '.')
    addurl = wrap(addurl, ['somethingWithoutSpaces', 'url'])

    def filldb(self, irc, msg, args, verification):
        """<yes>
        Loads the files verda.txt, noreg.txt and postnummer.txt into the local
        database.
        """
        path = os.path.dirname(__file__)
        world = os.path.join(path, 'verda.txt')
        norge = os.path.join(path, 'noreg.txt')
        postnr = os.path.join(path, 'postnummer.txt')
        dbsFilled = 0
        db = self.getDb('')
        cursor = db.cursor()

        cursor.execute("SELECT COUNT(*) FROM norge")
        results = cursor.fetchall()
        if (results[0][0] == 0):
            dbsFilled += 1
            cursor.execute("""BEGIN""")
            f = open(norge)
            for line in f.readlines():
                w = line.split('\t')
                cursor.execute("""INSERT INTO norge (kommunenr, name, priority,
                        locationtypenn, locationtypebn, locationtypeen,
                        municipality, county, lat, lon, amsl, urlnn, urlbm, urlen)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (w[0], w[1], w[2], w[3], w[4], w[5], w[6], w[7], w[8], w[9], w[10], w[11], w[12], w[13],))
            cursor.execute("""COMMIT""")

        cursor.execute("SELECT COUNT(*) FROM world")
        results = cursor.fetchall()
        if (results[0][0] == 0):
            dbsFilled += 1
            cursor.execute("""BEGIN""")
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
            cursor.execute("""COMMIT""")

        cursor.execute("SELECT COUNT(*) FROM postal")
        results = cursor.fetchall()
        if (results[0][0] == 0):
            dbsFilled += 1
            cursor.execute("""BEGIN""")
            f = open(postnr)
            for line in f.readlines():
                w = line.split('\t')
                cursor.execute("""INSERT INTO postal (postnr, name, type,
                        kommunenr, lat, lon, note, urlnn, urlbm, urlen) VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (w[0], w[1], w[2], w[3], w[4],
                            w[5], w[6], w[7], w[8], w[9],))
            cursor.execute("""COMMIT""")
        db.commit()
        plural = lambda n: 's' if int(n) > 1 else ''
        irc.reply("%s database%s filled." % (dbsFilled, plural(dbsFilled)))

    filldb= wrap(filldb, [('checkCapability', 'owner'), ('literal',
        'yes')])

    """ This function is called by magic. """
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
                          channel TEXT,
                          CONSTRAINT unq UNIQUE (alias, channel)
                          )""")
        db.commit()
        return db


Class = Yr
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
