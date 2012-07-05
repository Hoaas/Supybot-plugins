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
import urllib2
import os.path
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

    def __init__(self, irc):
        self.__parent = super(Yr, self)
        self.__parent.__init__(irc)

    def _sunRise(self, html):
        name = self._findName(html)
        
        try:
            html = html[html.find('yr-table-sunmoon'):]
            html = html[html.find('txt-left'):]
            html = html[html.find('>')+1:]
            html = html[:html.find('</table>')]
            sunrise = html[:html.find('</td>')]

            html = html[html.find('txt-left yr-table-cell-border-left'):]
            html = html[html.find('>')+1:]
            sundown = html[:html.find('</td>')]
        except:
            irc.reply('Sorry, failed to retrieve sunrise and/or sunset from ' + url)
            return None
        if not sundown:
            return sunrise + " (" + name + ")"
        return sunrise + ". " + sundown + ". (" + name + ")"

    def _moonRise(self, html):
            #<ul class="sunrise">
            #<li>Det er midnattssol, sola går ikke ned.</li>
            #</ul>
            #<ul class="moonrise">
            #<li title="10.05.2010 står månen opp 1:44">Månen opp 01:44</li>
            #<li title="10.05.2010 går månen ned 19:53">Månen ned 19:53</li>
            # </ul>
        name = self._findName(html)
        try:
            html = html[html.find('yr-table-sunmoon'):]
            html = html[html.find('txt-left'):]
            html = html[html.find('>')+1:]
            html = html[html.find('txt-left'):]
            html = html[html.find('>')+1:]
            html = html[:html.find('</table>')]
            moonrise = html[:html.find('</td>')]
            
            html = html[html.find('txt-left'):]
            html = html[html.find('>')+1:]
            html = html[html.find('txt-left'):]
            html = html[html.find('>')+1:]
            moondown = html[:html.find('</td>')]
        
        except:
            irc.reply('Sorry, failed to retrieve moonrise and/or moonset from ' + url)
            return None
        if not moondown:
            return moonrise + " (" + name + ")"
        return moonrise + ". " + moondown + ". (" + name + ")"
        
    def _findName(self, html):
        # Find the following:
        # <div class="title-crumbs">
        # last <li>s before </ul>
        htmltemp = html
        where = '<div class="yr-content-title clearfix">a'
        temp = html.find(where)+len(where)
        startofname = html.find('<h1>', temp) + len('<h1>')
        endofname = html.find('</h1>', startofname)
        name = html[startofname:endofname]
        name = name.replace('<span>', ' ')
        name = name.replace('</span>', '')
        name = name.replace('<strong>', '')
        name = name.replace('</strong>', '')
        name = name.replace("  ", " ") # Remove double space in some names.
        return name
                
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
        
        try:
            url.encode('iso-8859-1')
            req = urllib2.Request(url)
            f = urllib2.urlopen(req)
            html = f.read()
        except:
            self.log.debug('Failed to read from ' + url)
            return -1
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
            # Might aswell exit at this point.
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
        # Defaults to "Trøndelag"
        if not loc:
            loc = 9
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
                    break
            # If we have gone through the loop and loc still isn't an integer  the location is not found
        
        # If number is outside the accepted range.
        if(loc < 1 or loc > 12):
            irc.reply('Sorry, ' + str(loc) + ' is not a valid location. \
Check "pollen list" for list of locations.')
            return
        # At this point loc is an integer from 1 to 12
        retstr = self._pollen(locations, loc)
        if (retstr == -1):
            irc.reply('Sorry, failed to retrieve pollentriks.')
        else:
            irc.reply(retstr)
    pollen = wrap(pollen, [additional('text')])    
    
    def sun(self, irc, msg, args, channel, alias):
        """[<channel>] [<alias>]

        <channel> is only necessary if the message isn't sent on the channel itself.
        Fetches information from the stored URL for the specified alias <alias>.
        If no alias is specified 'default' is used.
        """
        url = self._getURL(irc, msg, args, channel, alias, None, None)
        if not url:
            return
        html = self._fetchHtml(irc, url)
        if not html:
            return
        
        sunrise = self._sunRise(html
                            )
        if not sunrise:
            return
        irc.reply(sunrise)
    sun = wrap(sun, ['channeldb', optional('anything')])
    
    def moon(self, irc, msg, args, channel, alias):
        """[<channel>] [<alias>]

        <channel> is only necessary if the message isn't sent on the channel itself.
        Fetches information from the stored URL for the specified alias <alias>.
        If no alias is specified 'default' is used.
        """
        url = self._getURL(irc, msg, args, channel, alias, None, None)
        if not url:
            return
        html = self._fetchHtml(irc, url)
        if not html:
            return
        
        moonrise = self._moonRise(html)
        
        if not moonrise:
            return
        irc.reply(moonrise)
    moon = wrap(moon, ['channeldb', optional('anything')])

    def location(self, irc, msg, args, channel, loc, url, lock):
        """[<channel>] <alias> <yr.no url> [--lock]

        <channel> is only necessary if the message isn't sent on the channel itself.
        Defines an alias <alias> for the url <yr.no url>.
        If --lock is spesified the alias can not be changed at a later date.
        """
        url = self._getURL(irc, msg, args, channel, loc, url, lock)
    location = wrap(location, ['channeldb', ('something'), ('HttpUrl'), optional(('literal', '--lock'))])
    
    def temp(self, irc, msg, args, channel, alias):
        """[<channel>] [<alias>]

        <channel> is only necessary if the message isn't sent on the channel itself.
        Fetches information from the stored URL for the specified alias <alias>.
        If no alias is specified 'default' is used.
        """
        
        # Sets or gets the URL, depending on the options used.
        url = self._getURL(irc, msg, args, channel, alias, None, None)
        if not url:
            return
        
        # Sinply fetches the html
        html = self._fetchHtml(irc, url)
        if not html:
            return
        
        name, weathertype, tempdesc, winddesc, tempdigit, winddigit = self._extractFromYr(html)
        if not tempdesc:
            irc.reply('Sorry, failed to retrieve weather from ' + url)
            return

        if tempdigit <= 0:
            tempdesc = ircutils.mircColor(tempdesc, 12) # Light blue
        else:
            tempdesc = ircutils.mircColor(tempdesc, 4) # Red
        # Only calculate windchill if there is a winddesc and temperature under 10°C and wind over 4.8 km/h
        if winddesc and tempdigit and winddigit and tempdigit < 10 and (winddigit*3.6) > 4.8:

            # T_wc = 13.12 + 0.6215 * T_a - 11.37 * V^0.16 + 0.3965 * T_a * V^0.16
            # T_wc = felt temperature, T_a = temperature in the air in °C, V = windspeed in km/h.
            windchill = 13.12 + 0.6215 * tempdigit - 11.37 * ((winddigit * 3.6)**0.16) + 0.3965 * tempdigit * ((winddigit * 3.6)**0.16)
            
            windchillstr = "%.1f°" % windchill
            # If not in english: use , instead of .
            if not "place" in url:
                windchillstr = windchillstr.replace(".", ",")

            if windchill <= 0:
                windchillstr = ircutils.mircColor(windchillstr, 12) # Light blue
            else:
                windchillstr = ircutils.mircColor(windchillstr, 4) # Red

            if weathertype:
                rep = '%s (%s). %s. %s (%s)' % (tempdesc, windchillstr, weathertype, winddesc, name)
            else:
                rep = '%s (%s). %s (%s)' % (tempdesc, windchillstr, winddesc, name)
        else:
            if weathertype and winddesc:
                rep = '%s. %s. %s (%s)' % (tempdesc, weathertype, winddesc, name)
            elif winddesc and not weathertype:
                rep = '%s. %s (%s)' % (tempdesc, winddesc, name)
            elif weathertype and not winddesc:
                rep = '%s. %s. (%s)' % (tempdesc, weathertype, name)
            elif not weathertype and not winddesc:
                rep = '%s (%s)' % (tempdesc, name)
        irc.reply(rep)
    temp = wrap(temp, ['channeldb', optional('anything')])


    def _extractFromYr(self, html):
        fullhtml = html
        try:
            firstenc = html.find('<table class="yr-table yr-table-station yr-popup-area">')
            html = html[firstenc:]
            # html is at this point starts with the closest measuring station
        except:
            self.log.debug('DEBUG: _extractFromYr in plugin yr failed at first try.')
            return None, None, None, None, None, None
        tempdesc = None
        # Run through tops 3 times, as long as we don't have any temp yet.
        for i in range(3):
            try:
                partialhtml = html[:html.find('</table>')]    # Store html for the closest weather station
                html = html[html.find('</table>')+8:]            # Store html for those that are further away
            except:
                self.log.debug('DEBUG: _extractFromYr in plugin yr failed at second try.')
                return None, None, None, None, None, None
            name, weathertype, tempdesc, winddesc, tempdigit, winddigit = self._getDataFromWeatherStation(partialhtml)
            # If we have a tempdesc, or we have tried all 3 weatherstations
            if (tempdesc or i == 2):
                if not tempdesc:
                    name, weathertype, tempdesc, winddesc, tempdigit, winddigit = self._getDataFromForecast(fullhtml)
                return name, weathertype, tempdesc, winddesc, tempdigit, winddigit    
    
    """ Returns None if error. 0 on success. 
    -1, -2, -3 or -4 if it is an error and it have been handled. (including output)
    Or it might actually return the url.
    """
    def _getURL(self, irc, msg, args, channel, alias, url, lock):
        dataDir = conf.supybot.directories.data
        
        channel = channel.lower()
        chandir = dataDir.dirize(channel)
        if not os.path.exists(chandir):
            os.makedirs(chandir)
            
        dataDir = dataDir.dirize(channel + "/Temperature.db")
        if not os.path.isfile(dataDir):
            open(dataDir, 'w')
        
        # If location is not set, it defaults to .. uhm, default
        if not alias:
            alias = 'default'
        newurl = False
        if url:
            # In case we get a random retarted url
            if url.find("yr.no/") == -1:
                irc.reply('That is not a valid yr.no-url.')
                return None
            newurl = True
        
        
        logfile = open(dataDir, 'r')
        # Reads the current log
        log = logfile.read()
        lines = log.splitlines()

        # For every line (in the Temperature.db file) we check if the first word 
        # is the location we are trying to set. If it is we need to replace it.
        for i in range(len(lines)):
            # Incase file have been edited manually, switch spaces for tab
            lines[i] = re.sub(r'\s+', '\t', lines[i])

            s = lines[i].split('\t')
            
            # Incase input location is found, could use 'if s[0] == loc.lower():' to be more exact.
            if s[0].startswith(alias.lower()):
                # this is the default hit
                # If there is no input url we read the url from the file (s[1])
                if not url:
                    url = s[1]
                    break
                # incase of url present
                else:
                    # == 'lock' is probably useless if wrap() is used right.
                    # If it is locked, nothing we can do anyway.
                    if len(s) == 3 and s[2] == 'lock':
                        irc.reply('The URL for this alias have been locked. Contact the owner of the bot if you want to change this.')
                        return None
                    
                    # If it is not locked but the locked option is present now.
                    lines[i] = alias.lower() + '\t' + url
                    if lock:
                        lines[i] = lines[i] + "\tlock"
                        
                    # Was not locked and still isn't. Just trying to set an url.
                    elif s[1] == url:
                        # Url and location already exists. We are done.
                        irc.reply('Alias and URL are already added.')
                        return None
                    
                    # Updates the url (rewrites the entire file)
                    open(dataDir, 'w')
                    logfile = open(dataDir, 'a')
                    for i in range(len(lines)):
                        logfile.write(lines[i] + '\n')
                    irc.replySuccess()
                    return None
            
        # If new location, append
        if newurl:
            logfile = open(dataDir, 'a')
            if lock and lock == '--lock':
                logfile.write(alias.lower() + '\t' + url + '\tlock\n')
            else:
                logfile.write(alias.lower() + '\t' + url + '\n')
            irc.replySuccess()
            return None
        # Happens when URL was not found in db.
        # Can be for both default and non-default location
        if not url:
            if alias == 'default':
                irc.reply("Add an URL for alias 'default' first.")
            else:
                irc.reply("Add an URL for this alias first.")
            return None
        else:
            return url
        
    def _fetchHtml(self, irc, url):
        try:
            url.encode('utf-8')
            req = urllib2.Request(url)
            f = urllib2.urlopen(req)
            html = f.read()
            return html
        except:
            irc.reply("I am truly sorry, but I seem to be unable to get any reasonable response from " + url)
            return None     

    def _getDataFromForecast(self, html):
        name, weathertype, tempdesc, winddesc, tempdigit, winddigit = None, None, None, None, None, None
        
        name = self._findName(html)
        try: 
            tag = '<table class="yr-table yr-table-overview2 yr-popup-area" summary="">'
            html = html[html.find(tag)+len(tag):]
            
            tag  = '<tbody>'
            html = html[html.find(tag)+len(tag):]
            
            tag = '<tr>'
            html = html[html.find(tag)+len(tag):]
            
            tag = '<td title="'
            html = html[html.find(tag)+len(tag):]
            
            weathertype = html[:html.find('.')]
            
            tag = 'title="'
            html = html[html.find(tag)+len(tag):]
            
            tag = ' '
            html = html[html.find(tag)+len(tag):]
            
            tempdesc = html[:html.find('. ')]

            tempdigit = float(html[:html.find('°')])
            
            
            tag = 'title="'
            html = html[html.find(tag)+len(tag):]

            precipitation = html[:html.find('. ')]
            
            tag = 'title="'
            html = html[html.find(tag)+len(tag):]
            
            winddesc = html[:html.find('. ')]
            
            start = winddesc.find(", ") + 2
            stop = winddesc.find("m/s")
            winddigit = float(winddesc[start:stop].replace(',', '.').strip())
        except:
            self.log.debug("DEBUG: _getDataFromForecast in yr failed.")
            pass
        return name, weathertype, tempdesc, winddesc, tempdigit, winddigit
    
    def _getDataFromWeatherStation(self, html):
        name, weathertype, tempdesc, winddesc, tempdigit, winddigit = None, None, None, None, None, None

        try: 
            # Find the first <strong> after <thead>. Cut from there to the second </strong>
            html = html[html.find('<thead>'):]
            html = html[html.find('<strong>')+8:]
            
            # Not using _findName(html) because we want the name for the current weather station
            name = html[:html.find('</strong>')]
             
            # Remove everything that's not in the <table> tag
            html = html[:html.find('</table>')]
        except:
            self.log.debug('DEBUG: _getDataFromWeatherStation in plugin yr failed at first try (extracting table).')
            return name, weathertype, tempdesc, winddesc, tempdigit, winddigit

        try:
            # weathertype
            html = html[html.find('<tbody>'):]
            html = html[html.find('<tr>')+4:]
            html = html[html.find('<tr>')+4:]
            htmltemp = html[:html.find('</td>')]
    
            loc = htmltemp.find("alt=")
            if (loc == -1):
                weathertype = None
            else:
                weathertype = htmltemp[loc+5:htmltemp.find('" />')]
        except:
            self.log.debug('DEBUG: _getDataFromWeatherStation in plugin yr failed at second try (weathertype).')
            return name, weathertype, tempdesc, winddesc, tempdigit, winddigit

        try: 
            # tempdesc
            html = html[html.find('</td>')+5:]
            htmltemp = html[:html.find('</td>')]
            loc = htmltemp.find('<td title="')
            if (loc == -1):
                tempdesc = None
            else:
                htmltemp = htmltemp[htmltemp.find('<span class'):]
                htmltemp = htmltemp[htmltemp.find('">')+2:]
                tempdesc = htmltemp[:htmltemp.find('<')]
        except:
            self.log.debug('DEBUG: _getDataFromWeatherStation in plugin yr failed at third try (tempdesc).')
            return name, weathertype, tempdesc, winddesc, tempdigit, winddigit

        try: 
            # winddesc
            html = html[html.find('</td>'):]
            html = html[html.find('<td'):]
            htmltemp = html[:html.find('</td>')+5]    # +5 here is a bit unsure. +0 removes 1 letter. Don't have time to fix this like it should be atm.
            loc = htmltemp.find('title="')
            htmltemp = htmltemp[:htmltemp.find('</td>')]
            loc = htmltemp.find('title=')

            if (loc == -1):
                winddesc = None
            else:
                htmltemp = htmltemp[htmltemp.find('alt="')+5:]
                winddesc = htmltemp[htmltemp.find('/>')+2:]
        except:
            self.log.debug('DEBUG: _getDataFromWeatherStation in plugin yr failed at fourth try (winddesc).')
            return name, weathertype, tempdesc, winddesc, tempdigit, winddigit

        try:
            
            # We know the last letter is °
            # Here be magic.
            tempdigit = float(tempdesc[0:tempdesc.find("°")].replace(',', '.'))
            if winddesc:
                start = winddesc.find(", ") + 2
                stop = winddesc.find("m/s")

                winddigit = float(winddesc[start:stop].replace(',', '.').strip())
            else:
                winddigit = None
        except:
            self.log.debug('DEBUG: _getDataFromWeatherStation in plugin yr failed at second try (weather station: ' + name + ').')
            # Try to find first forecast i XML
            return name, weathertype, tempdesc, winddesc, tempdigit, winddigit


        
        self.log.debug('Name: ' + str(name))
        self.log.debug('Weather type: ' + str(weathertype))
        self.log.debug('Temperature description: ' + str(tempdesc))
        self.log.debug('Wind description: ' + str(winddesc))
        self.log.debug('Temperature as digit: ' + str(tempdigit))
        self.log.debug('Wind speed as digit: ' + str(winddigit))
        self.log.debug('{0}. {1}. {2}'.format(tempdesc, weathertype, winddesc))
        
        return name, weathertype, tempdesc, winddesc, tempdigit, winddigit
    
Class = Yr


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
