# coding=utf8
###
# Copyright (c) 2011, Terje Hoås
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

import urllib2
import json
import datetime
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class AtB(callbacks.Plugin):
	"""Returns real time data on next passing on busses in Trondheim. 
	Gets data from BusBuddy API (http://api.busbuddy.norrs.no:8080/) which is supplied unofficially from AtB (atb.no).
	Also calculate it the price for a season card."""
	threaded = True

	def atb(self, irc, msg, args, name):
		"""<bus stop>
        Returns time until passing of the next busses for the spesified bus stop. 
        Returns time on the first bus stop with matching name. Not alphabetic.
        """

		idList = self._getIdList(name)

		if (idList == -1):
			irc.reply("Error. Kunne ikke åpne URLen. hoaas.no er sikkert nede.")
			self.log.debug("Error: Could not open URL. (AtB / _getIdList())")
			return
		elif(len(idList) < 1):
			irc.reply("Ingen holdeplasser som starter på \"" + name + "\" ble funnet.")
			return

		stops = []
		for lists in idList:
			stops.append(lists[0])          # Create a list over all the matching stops
		stopsset = set(stops)               # Remove all duplicates


		selectedstop = list(stopsset).pop(0)
		newlist = []
		for li in idList:
			if(li[0] == selectedstop):
				newlist.append(li)

		rettowardscity = None
		retfromcity = None

		for li in newlist:                    # For all busstops. Should be only 2.
			id = li[1]
			busstopname = li[0]
			times, towardsCity = self._getTimes(id)
			if (times == -1):                # In case of errors
				irc.reply("Error: Could not open URL. API probably down.")
				return
			elif (times == -2):
				irc.reply("Error: No data for busstop " + busstopname +  ".")
				return
			elif (times == -3):
				continue
			if(towardsCity):
				rettowardscity = unicode(busstopname, 'utf8') + " mot sentrum: " + times
			else:
				retfromcity = unicode(busstopname, 'utf8') + " fra sentrum: " + times
		if(rettowardscity):
			irc.reply(rettowardscity.encode('utf8'))
		if(retfromcity):
			irc.reply(retfromcity.encode('utf8'))
		if(not rettowardscity and not retfromcity):
			irc.reply("Sorry, ingen informasjon om holdeplass.")
	atb = wrap(atb, ['text'])

	"""Returns a list of dictionaries.
	Each dictionary contains BusStopName:BusStopID.
	Empty list means zero busstops was found.
	"""
	def _getIdList(self, name):
	#    url = "http://api.busbuddy.norrs.no:8080/api/1.2/busstops"     # URL to JSON data that contains list over busstops
		url = "http://hoaas.no/busstops"   # Alternative local url
		#apikey = "your-api-key-here"         # Private API key. Please don't use this :(

		try:
			req = urllib2.Request(url)
			#req.add_header('X-norrs-busbuddy-apikey', apikey)   # Recommended to add API-key in header. Could be added in url as "http://example.com/bus?apikey=23141234"
			stream = urllib2.urlopen(req)
			data = stream.read()
		except:
			return -1

		data = json.loads(data)
		hitlist = []
		for busstop in data["busStops"]:
			if ( busstop["name"].encode('utf8').lower().startswith(name.lower()) or
				 ( busstop["nameWithAbbreviations"] and
				   busstop["nameWithAbbreviations"].encode('utf8').lower().startswith(name.lower()) ) ):
				hitlist.append((busstop["name"].encode('utf8'), busstop["locationId"]))
		return hitlist

	"""Get the passing times of the next busses for the spesified ID.
	Returns a string with which bus lines and how long until the bus shows up.
	The return string do not contain the name of the busstop.
	"""
	def _getTimes(self, id):
		url = "http://api.busbuddy.norrs.no:8080/api/1.3/departures/" # <locationId>
		url += str(id)
		apikey = "your-api-key-here"         # Private API key. Please don't use this :(

		try:
			req = urllib2.Request(url)
			req.add_header('X-norrs-busbuddy-apikey', apikey)
			stream = urllib2.urlopen(req)
			data = stream.read()
		except:
			return -1, -1
		if (len(data) == 0):
			return -3, -3
		try:
			data = json.loads(data)
		except:
			return -2, -2
#		print "--------- This is the full json ---------"
#		print json.dumps(data, sort_keys=True, indent=4)
#		print "--------- That was it! ---------"
		ret = ""        # Return-string
		for dest in data["departures"]:
			now = datetime.datetime.now()
			passing = dest["registeredDepartureTime"]
			passing = datetime.datetime.strptime(passing, "%Y-%m-%dT%H:%M:%S.000")  # Right formatting
			td = passing - now      # Time delta
			space = " om "
			if not dest["isRealtimeData"]:
				space += "ca. "
			ret += "#" + dest["line"] + space + str(td.seconds / 60) + " min. "
		return ret, data["isGoingTowardsCentrum"]   # Warning. Might be changed to City soon.

# For testing only. Uncomment and add help for supybot.test to work.
	"""
	def calcprice(self, irc, msg, args, days, student):
		#Add help here. 
		#
        # Day 1:          62.50
        # Day 7-39:       21.50
        # Day 40-159:     19.75
        # Day 160-185:    18.50
		if days >= 7 and days <= 39:
			prday = 21.50
		elif days >= 40 and days <= 159:
			prday = 19.75
		elif days >= 160 and days <= 185:
			prday = 18.50

		price = 62.50 + (prday * (days - 1))
		price = price * 0.854
		price = int(round(price / 5)) * 5 # Price for adult
		if(price == 165):
			price -= 5
		if student:
			price = price * 0.6 # Students get 40% off. Woo.
			price = int(round(price / 5)) * 5 # Price for student
		irc.reply(price)
	calcprice = wrap(calcprice, ['int', 'boolean'])
	"""


	def tkort(self, irc, msg, args, input):
		"""<number of days | YYYY-MM-DD>

		Returnerer studentpris på t:kort for x dager eller fram til gitt dato,
		der dato er siste dag kortet er gyldig. Dagen i dag er ikke medregnet.
		"""
		try:
			days = int(input)
		except ValueError:
			try:
				year = int(input[0:4])
				month = int(input[5:7])
				day = int(input[8:10])
				td = datetime.datetime(year, month, day) - datetime.datetime.now()
				if td.days < 0:
					irc.reply("Are you from the past?")
					return
				days = td.days + 1 # +1 to start to count on 1 tomorrow.
			except:
				irc.reply("Ikke gyldig dato. Dato må være på formen YYYY-MM-DD.")
				return
		if days < 7:
			days = 7
		elif days > 185:
			days = 185
		price = self._calcPrice(days, True) # False = adult, True = student.
		tail = ""
		if days >= 36 and days < 40:
			tail = " NB! Det blir billigere pr. dag fra og med dag 40. Du kan spare penger på å kjøpe for et par dager til."
		elif days >= 149 and days < 160:
			tail = " NB! Det blir billigere pr. dag fra og med dag 160. Du kan spare penger på å kjøpe for et par dager til."
		irc.reply("Studentpris for " + str(days) + " dager er " + str(price) + " kr." + tail)
	tkort = wrap(tkort, ['text'])
	
	"""
	Used by tkort to calculate the price for 'days' number of days.
	The argument 'student' is boolean.
	"""
	def _calcPrice(self, days, student):
		# Day 1:          62.50
		# Day 7-39:       21.50
		# Day 40-159:     19.75
		# Day 160-185:    18.50
		if days >= 7 and days <= 39:
			prday = 21.50
		elif days >= 40 and days <= 159:
			prday = 19.75
		elif days >= 160 and days <= 185:
			prday = 18.50

		price = 62.50 + (prday * (days - 1))
		price = price * 0.854
		price = int(round(price / 5)) * 5 # Price for adult
		if(price == 165):
			price -= 5

		if student:
			price = price * 0.6 # Students get 40% off. Woo.
			price = int(round(price / 5)) * 5 # Price for student
		return price

Class = AtB


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
