###
# Copyright (c) 2010, William Donaldson
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

import apisettings
import supybot.dbi as dbi
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.utils.str import *
import pylast
import pickle
import re

class LastFMUsernameNotSetError(Exception):
    pass

class YouAreAnIdiotError(Exception):
    pass

class IncorrectPeriodError(Exception):
    pass

# I would be lying if I said I knew how this DB code works. I wrote it so long
# ago and never commented it. Oops.

class LastFMRecord(dbi.Record):
    __fields__ = [
        'ircuser',
        'lfmuser',
        'recs'
        ]
    
    def __str__(self):
        return self.lfmuser

class DbiLastFMDB(dbi.DB):
    Record = LastFMRecord
    
    def hasRecord(self, ircuser):
        return (not (self.get(ircuser) is None))
        
    def add(self, ircuser, lfmuser):
        if self.hasRecord(ircuser):
            self.set(ircuser, lfmuser)
        else:
            record = self.Record(ircuser=ircuser, lfmuser=lfmuser, recs=None)
            super(self.__class__, self).add(record)
    
    def set(self, ircuser, lfmuser):
        record = self.get(ircuser)
        record.lfmuser = lfmuser
        super(self.__class__, self).set(record.id, record)
    
    def get(self, ircuser):
        p = (lambda x: x.ircuser.lower() == ircuser.lower())
        try:
            return super(self.__class__, self).select(p).next()
        except StopIteration:
            return None
    
    def addRec(self, ircuser, rec):
        record = self.get(ircuser)
        if record.recs == None:
            recs = [rec]
        else:
            recs = pickle.loads(record.recs)
            recs.append(rec)
        record.recs = pickle.dumps(recs)
        super(self.__class__, self).set(record.id, record)
    
    def getRecs(self, ircuser):
        record = self.get(ircuser)
        if record.recs == None:
            return None
        else:
            return pickle.loads(record.recs)
    
    def clearRecs(self, ircuser):
        record = self.get(ircuser)
        record.recs = None
        super(self.__class__, self).set(record.id, record)

class Recommendation:
    def __init__(self, sender, recipient, data):
        self.sender = sender
        self.recipient = recipient
        self.data = data

LastFMDB = plugins.DB('LastFM', {'flat': DbiLastFMDB})
            
def getNetworkObject(API_KEY, API_SECRET):
    """Gets the network object needed to get information."""
    network = None
    try:
        network = pylast.get_lastfm_network(api_key = API_KEY, api_secret = API_SECRET)
        network.enable_caching() # enables caching for certain calls (see pylast.py)
    except pylast.WSError, e:
        irc.error("Houston, we have a problem. %s" % e.get_id())
    return network

def getLastFMUsername(username):
    """If this is a IRC user in the database, grab their Last.fm
    username. If not, this must be a Last.fm username."""
    if db.hasRecord(username):
        return db.get(username).lfmuser
    else:
        return username

db = LastFMDB()
network = getNetworkObject(apisettings.API_KEY, apisettings.API_SECRET)

album_regexp = re.compile("(?P<artist>.+) - (?P<album>.+)")

def format_number(number):
    if int(number) > 999 or int(number) < -999:
        number = str(number)
        flag = ""
        if number[0] is "-":
            number = number[1:]
            flag = "-"
        c = 1
        for i in range(0, len(number))[::-1]:
            if c == 3:
                if i != 0:
                    number = number[:i] + "," + number[i:]
                    c = 1
            else:
                c += 1
        number = flag + number
    return number

class LastFM(callbacks.Plugin):
    """@list LastFM"""
    threaded = True
    
    def __init__(self, irc):
        self.__parent = super(LastFM, self)
        self.__parent.__init__(irc)
    
    def compare(self, irc, msg, args, usera, userb=None):
        """<user 1> [<user 2>]
        
        Calculates tasteometer information for two users."""
        try:
            num_results = 10    # number of similar artists shown
            outputString = "%s and %s are %s%% alike.%s"
            bothLikeString = " %s both like %s."
            theyoryou = "They"
            if userb == None:
                userb = usera
                usera = msg.nick
                theyoryou = "You"
                if not db.hasRecord(msg.nick):
                    raise LastFMUsernameNotSetError
            userARef = network.get_user(getLastFMUsername(usera))
            userBRef = network.get_user(getLastFMUsername(userb))
            if userARef.get_name().lower() == userBRef.get_name().lower():
                raise YouAreAnIdiotError
            try:
                tasteometer = userARef.compare_with_user(userBRef)
            except:
                irc.error("We're recharging the taste-o-meter's batteries. Check back soon for your compatibility score!")
                return
            #score = int(float(tasteometer[0]) * 100)
            score = round(float(tasteometer[0]) * 100, 2)
            similarArtists = [x.get_name() for x in tasteometer[1]]
            similarText = commaAndify(similarArtists)
            bothLike = ""
            if len(similarText) is not 0:
                bothLike = bothLikeString % (theyoryou,
                                            similarText)
            output = outputString % (usera, 
                                    userb,
                                    score, 
                                    bothLike)
            irc.reply(output.encode("utf-8"))
        except LastFMUsernameNotSetError:
            irc.error("Set your Last.FM nick first using setusername.")
        except pylast.WSError, e:
            irc.error(str(e))
        except YouAreAnIdiotError:
            irc.error("You can't compare a person to themselves.")
    compare = wrap(compare, ['anything', optional('anything')])
    
    def similar(self, irc, msg, args, artist):
        """<artist>
        
        Returns a list of similar artists."""
        try:
            outputString = "%s is similar to %s."
            outputStringNone = "%s is not similar to anyone."
            artistInstance = network.get_artist(artist)
            artistName = artistInstance.get_name(properly_capitalized=True)
            similarArtists = artistInstance.get_similar(10)
            similarArtistsList = [x.item.get_name() for x in similarArtists]
            similarText = commaAndify(similarArtistsList).encode("utf-8")
            if len(similarText) is 0:
                output = outputStringNone % artistName
            else:
                output = outputString % (artistName, similarText)
            irc.reply(output.encode("utf-8"))
        except pylast.WSError, e:
            irc.error(str(e))
    similar = wrap(similar, ['text'])
    
    def bio(self, irc, msg, args, artist):
        """<artist>
        
        Returns a summary of Last.FM's biography of the artist."""
        try:
            artistInstance = network.get_artist(artist)
            summary = artistInstance.get_bio_summary()
            if summary != None and summary != "":
                summary = re.sub("\<[^<]+\>", "", summary)
                summary = re.sub("\s+", " ", summary)
            else:
                irc.error("No bio is available for this artist.")
            irc.reply(summary.encode('utf-8'))
        except pylast.WSError, e:
            irc.error(str(e))
    bio = wrap(bio, ['text'])
    
    def artist(self, irc, msg, args, artist):
        """[<artist>]
        
        Returns some information on the artist. If no artist is given, returns
        some information on the currently playing artist."""
        try:
            outputString = "%s has %s %s.%s%s%s%s"
            tagsString = " Tags: %s."
            albumsString = " Popular albums: %s."
            tracksString = " Popular tracks: %s."
            urlString = " %s"
            if artist != None:
                artistInstance = network.get_artist(artist)
            else:
                username = msg.nick
                if not db.hasRecord(msg.nick):
                    raise callbacks.ArgumentError
                userRef = network.get_user(getLastFMUsername(username))
                nowPlaying = userRef.get_now_playing()
                output = ""
                if nowPlaying is not None:
                    artistInstance = nowPlaying.get_artist()
                else:
                    raise callbacks.ArgumentError
            artistName = artistInstance.get_name(properly_capitalized=True)
            topTags = artistInstance.get_top_tags(limit=3)
            topTags = [x.item.get_name() for x in topTags]
            topTags = commaAndify(topTags)
            if len(topTags) > 0:
                topTags = tagsString % topTags
            topAlbums = artistInstance.get_top_albums()
            if len(topAlbums) > 3:
                topAlbums = topAlbums[:3]
            topAlbums = commaAndify([x.item.get_name() for x in topAlbums])
            if len(topAlbums) > 0:
                topAlbums = albumsString % topAlbums
            listeners = artistInstance.get_listener_count()
            topTracks = artistInstance.get_top_tracks()
            if len(topTracks) > 3:
                topTracks = topTracks[:3]
            topTracksText = commaAndify([x.item.get_name() for x in topTracks])
            if len(topTracksText) > 0:
                topTracksText = tracksString % topTracksText         
            url = artistInstance.get_url()
            if len(url) > 0:
                url = urlString % url
            listener = "listener" if (listeners == 1) else "listeners"
            output = outputString % (artistName, format_number(listeners), listener, topTags, topAlbums, topTracksText, url)
            irc.reply(output.encode("utf-8"))
        except LastFMUsernameNotSetError:
            irc.error("Set your Last.FM nick first using setusername.")
        except YouAreAnIdiotError:
            irc.error("You're not playing anything.")
        except pylast.WSError, e:
            irc.error(str(e))
    artist = wrap(artist, [optional('text')])
    
    def album(self, irc, msg, args, data):
        """[<artist> - <album>]
        
        Returns some information on the album. If no album is given, returns
        some information on the currently playing album."""
        try:
            outputString = "%s by %s has %s listener%s and %s track%s%s.%s%s"
            tracksString = ": %s"
            tagsString = " Top tags: %s."
            urlString = " %s"
            if data != None:
                m = album_regexp.match(data)
                artist = m.group('artist')
                album = m.group('album')
                albumInstance = network.get_album(artist, album)
            else:
                username = msg.nick
                if not db.hasRecord(msg.nick):
                    raise callbacks.ArgumentError
                userRef = network.get_user(getLastFMUsername(username))
                nowPlaying = userRef.get_now_playing()
                output = ""
                if nowPlaying is not None:
                    albumInstance = nowPlaying.get_album()
                else:
                    raise callbacks.ArgumentError
            artistName = albumInstance.get_artist().get_name(properly_capitalized=True)
            albumName = albumInstance.get_name(properly_capitalized=True)
            listeners = albumInstance.get_listener_count()
            listener_s = "s"
            if listeners == "1":
                listener_s = ""
            tracks = albumInstance.get_tracks()
            trackCount = len(tracks)
            track_s = "s"
            if trackCount is 1:
                track_s = ""
            tracksText = commaAndify([x.get_name() for x in tracks])
            if trackCount > 0:
                tracksText = tracksString % tracksText
            topTags = albumInstance.get_top_tags(limit=3)
            topTags = commaAndify([x.get_name() for x in topTags])
            if len(topTags) > 0:
                topTags = tagsString % topTags
            url = albumInstance.get_url()
            if len(url) > 0:
                url = urlString % url
            output = outputString % (albumName, artistName, format_number(listeners), listener_s, format_number(trackCount), track_s, tracksText, topTags, url)
            irc.reply(output.encode("utf-8"))
        except AttributeError, e:
            if str(e) == "'NoneType' object has no attribute 'group'":
                raise callbacks.ArgumentError
            else:
                raise
        except LastFMUsernameNotSetError:
            irc.error("Set your Last.FM nick first using setusername.")
        except YouAreAnIdiotError:
            irc.error("You're not playing anything.")
        except pylast.WSError, e:
            irc.error(str(e))
    album = wrap(album, [optional('text')])
    
    def track(self, irc, msg, args, data):
        """[<artist> - <track title>]
        
        Returns some information on the track. If no track is given,
        will return some information on your currently playing track."""
        try:
            outputString = "%s by %s%s has %s listener%s%s and is %s long.%s%s"
            albumString = " is on the album %s,"
            tagsString = " Top tags: %s."
            urlString = " %s"
            if (data != None):
                m = album_regexp.match(data)
                artist = m.group('artist')
                trackTitle = m.group('album')
                trackInstance = network.get_track(artist, trackTitle)
            else:
                username = msg.nick
                if not db.hasRecord(msg.nick):
                    raise callbacks.ArgumentError
                userRef = network.get_user(getLastFMUsername(username))
                nowPlaying = userRef.get_now_playing()
                output = ""
                if nowPlaying is not None:
                    trackInstance = nowPlaying
                else:
                    raise callbacks.ArgumentError
            artistName = trackInstance.get_artist().get_name(properly_capitalized=True)
            trackName = trackInstance.get_name(properly_capitalized=True)
            albumName = trackInstance.get_album()
            if albumName is not None:
                albumName = albumName.get_name().encode("utf-8")
            else:
                albumName = ""
            listeners = trackInstance.get_listener_count()
            listener_s = "s"
            if listeners == "1":
                listener_s = ""
            duration = trackInstance.get_duration()
            duration = duration / 1000
            seconds = str(duration % 60)
            if len(seconds) == 1:
                seconds = "0" + seconds
            duration = str(duration / 60) + ":" + seconds
            comma = ""
            albumText = ""
            if len(albumName) > 0:
                albumText = albumString % albumName
                comma = ","
            topTags = trackInstance.get_top_tags(limit=3)
            topTags = commaAndify([x.item.get_name() for x in topTags]).encode("utf-8")
            if len(topTags) > 0:
                topTags = tagsString % topTags
            url = trackInstance.get_url()
            if len(url) > 0:
                url = urlString % url
            output = outputString % (trackName, artistName, albumText, format_number(listeners), listener_s, comma, duration, topTags, url)
            irc.reply(output.encode("utf-8"))
        except AttributeError, e:
            if str(e) == "'NoneType' object has no attribute 'group'":
                raise callbacks.ArgumentError
            else:
                raise
        except LastFMUsernameNotSetError:
            irc.error("Set your Last.FM nick first using setusername.")
        except YouAreAnIdiotError:
            irc.error("You're not playing anything.")
        except pylast.WSError, e:
            irc.error(str(e))
    track = wrap(track, [optional('text')])
    
    def setusername(self, irc, msg, args, username, nick):
        """<Last.FM username> [<nick>]
        
        Saves your (or someone else's, if <nick> is provided) Last.FM
        username."""
        if (nick != None) and (username == ""):
            username = nick
            nick = None
        if nick == None:
            nick = msg.nick
        db.add(nick, username)
        irc.reply("Okay.")
    setusername = wrap(setusername, ['text', optional('seenNick')])
    
    def getusername(self, irc, msg, args):
        """takes no arguments
        
        Returns your Last.FM username."""
        try:
            lfmusername = db.get(msg.nick)
            irc.reply(lfmusername)
        except Exception, e:
            irc.error(str(e))
    getusername = wrap(getusername)
    
    def user(self, irc, msg, args, username):
        """[<nick>|<Last.FM username>]
        
        Returns some info on the user's Last.FM account."""
        try:
            outputString = "%s %s and has listened to %s %s. %s"
            if username is None:
                username = msg.nick
                if not db.hasRecord(msg.nick):
                    raise LastFMUsernameNotSetError
            userRef = network.get_user(getLastFMUsername(username))
            url = userRef.get_url()
            altuser = userRef.get_name()
            usernames = ""
            if username.lower() == altuser.lower():
                usernames = altuser
            else:
                usernames = "%s (%s)"%(username, altuser)
            usernames.encode("utf-8")
            try:
                nowPlaying = userRef.get_now_playing()
                songText = ""
                if nowPlaying is not None:
                    song = nowPlaying.get_artist().get_name() + " - " + nowPlaying.get_title()
                    songText = "is now playing %s" % song.encode("utf-8")
                else:
                    recentTrack = userRef.get_recent_tracks(limit=1)[0].track
                    song = recentTrack.get_artist().get_name() + " - " + recentTrack.get_title()
                    songText = "last heard %s" % song.encode("utf-8")
            except IndexError:
                nowPlaying = None
                songText = "has never listened to any song"
            playcount = userRef.get_playcount()
            song = "songs"
            if playcount is 1:
                song = "song"
            output = outputString % (usernames, songText, format_number(playcount), song, url)
            irc.reply(output.encode("utf-8"))
        except LastFMUsernameNotSetError:
            irc.error("Set your Last.FM nick first using setusername.")
        except pylast.WSError, e:
            irc.error(str(e))
    user = wrap(user, [optional('text')])
    
    def np(self, irc, msg, args):
        """takes no arguments
        
        Returns your currently playing song."""
        try:
            outputString = "You're now playing: %s - %s."
            if not db.hasRecord(msg.nick):
                raise LastFMUsernameNotSetError
            userRef = network.get_user(getLastFMUsername(msg.nick))
            nowPlaying = userRef.get_now_playing()
            output = ""
            if nowPlaying is not None:
                artist = nowPlaying.get_artist().get_name().encode("utf-8")
                track = nowPlaying.get_name().encode("utf-8")
                output = outputString % (artist, track)
            else:
                output = "You're not playing anything."
            irc.reply(output.encode("utf-8"))
        except LastFMUsernameNotSetError:
            irc.error("Set your Last.FM nick first using setusername.")
        except pylast.WSError, e:
            irc.error(str(e))
    np = wrap(np)
    
    def tag(self, irc, msg, args, tag):
        """<tag>
        
        Returns some info on the tag <tag>."""
        try:
            summaryLength = 260
            outputString = "%s%s%s%s"
            summaryString = "\"%s\" "
            artistsString = " Top artists: %s."
            #tracksString = " Top tracks: %s."
            #tagsString = " Similar tags: %s."
            sString = "'s%s"
            nothingString = " has no top artists."
            urlString = " %s"
            tagRef = network.get_tag(tag)
            tag = tagRef.get_name(properly_capitalized = True)
            tag = tag[0].upper() + tag[1:]
            summary = pylast._extract(tagRef._request("tag.getInfo", True), "summary")
            if summary != None and summary != "":
                summary = re.sub("\<[^<]+\>", "", summary)
                summary = re.sub("\s+", " ", summary)
                summary = summary[:summaryLength] + "..." if (summary[:summaryLength] != summary) else summary
            topArtists = tagRef.get_top_artists()
            if len(topArtists) > 3:
                topArtists = topArtists[:3]
            topArtistsText = commaAndify([x.item.get_name() for x in topArtists])
            if len(topArtistsText) > 0:
                topArtistsText = artistsString % topArtistsText
            
            #topTracks = tagRef.get_top_tracks()
            #if len(topTracks) > 3:
            #    topTracks = topTracks[:3]
            #topTracksText = commaAndify([x.item.get_artist().get_name() 
            #    + " - " + x.item.get_name() for x in topTracks]).encode("utf-8")
            #if len(topTracksText) > 0:
            #    topTracksText = tracksString % topTracksText
            
            #similarTags = tagRef.get_similar()
            #if len(similarTags) > 3:
            #    similarTags = similarTags[:3]
            #similarTagsText = commaAndify([x.get_name() for x in similarTags])
            #if len(similarTagsText) > 0:
            #    similarTagsText = tagsString % similarTagsText
            
            data = sString % (topArtistsText)
            if len(topArtistsText) is 0:
                data = nothingString
            else:
                data = data[:3] + data[3].lower() + data[4:]
            url = tagRef.get_url()
            if len(url) > 0:
                url = urlString % url
            summary = summaryString % summary if (summary != None and summary != "") else ""
            output = outputString % (summary, tag, data, url)
            irc.reply(output.encode("utf-8"))
        except pylast.WSError, e:
            irc.error(str(e))
    tag = wrap(tag, ["text"])
    
    def similartags(self, irc, msg, args, tag):
        """<tag>
        
        Returns a list of tags similar to <tag>."""
        try:
            numberOfTags = 15
            outputString = "%s"
            sString = "'s similar tags: %s"
            nothingString = " has no similar tags."
            tagRef = network.get_tag(tag)
            tag = tagRef.get_name(properly_capitalized = True)
            tag = tag[0].upper() + tag[1:]
            
            similarTags = tagRef.get_similar()
            if len(similarTags) > numberOfTags:
                similarTags = similarTags[:numberOfTags]
            similarTagsText = commaAndify([x.get_name() for x in similarTags])
            if len(similarTagsText) > 0:
                similarTagsText = sString % similarTagsText
            
            if len(similarTagsText) == 0:
                output = tag + nothingString
            else:
                output = tag + similarTagsText
            irc.reply(output.encode("utf-8"))
        except pylast.WSError, e:
            irc.error(str(e))
    similartags = wrap(similartags, ["text"])
        
    
    def friends(self, irc, msg, args, usera, userb=None):
        """<user 1> [<user 2>]
        
        See if you (or user 2) is/are Last.fm friends with user 1."""
        try:
            outputString = "%s"
            isorare = "is"
            if userb == None:
                userb = usera
                usera = msg.nick
                isorare = "are"
                if not db.hasRecord(msg.nick):
                    raise LastFMUsernameNotSetError
            userARef = network.get_user(getLastFMUsername(usera))
            userBRef = network.get_user(getLastFMUsername(userb))
            if userARef.get_name().lower() == userBRef.get_name().lower():
                raise YouAreAnIdiotError
            userAFriends = userARef.get_friends(limit=None)
            theyAreFriends = False
            for i in userAFriends:
                if i.get_name().lower() == userBRef.get_name().lower():
                    theyAreFriends = True
                    break
            if theyAreFriends:
                outputString = "Yes, %s %s friends with %s."
            else:
                outputString = "No, %s %s not friends with %s."
            nameone = usera
            if isorare == "are":
                nameone = "you"
            output = outputString % (nameone, isorare, userb)
            irc.reply(output.encode("utf-8"))
        except LastFMUsernameNotSetError:
            irc.error("Set your Last.FM nick first using setusername.")
        except pylast.WSError, e:
            irc.error(str(e))
        except YouAreAnIdiotError:
            irc.error("A person cannot be friends with themselves.")
    friends = wrap(friends, ['anything', optional('anything')])
    
    class top(callbacks.Commands):
        def artists(self, irc, msg, args, period, username):
            """[<period>] [<nick>|<Last.FM username>]
            
            Returns some info on the user's top artists. <period> can
            be 3, 6, or 12 to show the top artists of the past 3, 6,
            or 12 months or left out to give the top overall artists."""
            try:
                outputString = "%s's top artists%s: %s"
                if period != None:
                    if period not in ('0', '3', '6', '12', 'w'):
                        username = period
                        period = None
                        
                if username is None:
                    username = msg.nick
                    if not db.hasRecord(msg.nick):
                        raise LastFMUsernameNotSetError
                userRef = network.get_user(getLastFMUsername(username))
                
                pPeriod = None
                durationText = ""
                if period == None or period == '0':
                    pPeriod = pylast.PERIOD_OVERALL
                    durationText = " of all time"
                if period == 'w':
                    pPeriod = pylast.PERIOD_7DAYS
                    durationText = " of the past week"
                if period == '3':
                    pPeriod = pylast.PERIOD_3MONTHS
                    durationText = " of the past 3 months"
                if period == '6':
                    pPeriod = pylast.PERIOD_6MONTHS
                    durationText = " of the past 6 months"
                if period == '12':
                    pPeriod = pylast.PERIOD_12MONTHS
                    durationText = " of the past year"
                if pPeriod == None:
                    raise IncorrectPeriodError
                topArtists = userRef.get_top_artists(pPeriod)
                if len(topArtists) > 10:
                    topArtists = topArtists[:10]
                topArtistsTexts = commaAndify(["" + x.item.get_name() 
                    + " (" + x.weight + " play" 
                    + ("" if x.weight == "1" else "s") + ")" for x in topArtists])
                output = outputString % (username, durationText, topArtistsTexts)
                irc.reply(output.encode("utf-8"))
            except IncorrectPeriodError:
                irc.error("The period specified must be either 3, 6, or 12.")
            except LastFMUsernameNotSetError:
                irc.error("Set your Last.FM nick first using setusername.")
            except pylast.WSError, e:
                irc.error(str(e))
        artists = wrap(artists, [optional('something'), optional('something')])
        
        def albums(self, irc, msg, args, period, username):
            """[<period>] [<nick>|<Last.FM username>]
            
            Returns some info on the user's top albums. <period> can
            be 3, 6, or 12 to show the top albums of the past 3, 6,
            or 12 months or left out to give the top overall albums."""
            try:
                outputString = "%s's top albums%s: %s"
                if period != None:
                    if period not in ('0', '3', '6', '12', 'w'):
                        username = period
                        period = None
                        
                if username is None:
                    username = msg.nick
                    if not db.hasRecord(msg.nick):
                        raise LastFMUsernameNotSetError
                userRef = network.get_user(getLastFMUsername(username))
                
                pPeriod = None
                durationText = ""
                if period == None or period == '0':
                    pPeriod = pylast.PERIOD_OVERALL
                    durationText = " of all time"
                if period == 'w':
                    pPeriod = pylast.PERIOD_7DAYS
                    durationText = " of the past week"
                if period == '3':
                    pPeriod = pylast.PERIOD_3MONTHS
                    durationText = " of the past 3 months"
                if period == '6':
                    pPeriod = pylast.PERIOD_6MONTHS
                    durationText = " of the past 6 months"
                if period == '12':
                    pPeriod = pylast.PERIOD_12MONTHS
                    durationText = " of the past year"
                if pPeriod == None:
                    raise IncorrectPeriodError
                topAlbums = userRef.get_top_albums(pPeriod)
                if len(topAlbums) > 8:
                    topAlbums = topAlbums[:8]
                topAlbumsTexts = commaAndify(["" 
                    + x.item.get_artist().get_name() + " - " 
                    + x.item.get_name()  + " (" + x.weight + " play"
                    + ("" if x.weight == "1" else "s") + ")"
                    for x in topAlbums])
                output = outputString % (username, durationText, topAlbumsTexts)
                irc.reply(output.encode("utf-8"))
            except IncorrectPeriodError:
                irc.error("The period specified must be either 3, 6, or 12.")
            except LastFMUsernameNotSetError:
                irc.error("Set your Last.FM nick first using setusername.")
            except pylast.WSError, e:
                irc.error(str(e))
        albums = wrap(albums, [optional('something'), optional('something')])
        
        def tracks(self, irc, msg, args, period, username):
            """[<period>] [<nick>|<Last.FM username>]
            
            Returns some info on the user's top tracks. <period> can
            be 3, 6, or 12 to show the top tracks of the past 3, 6,
            or 12 months or left out to give the top overall tracks."""
            try:
                outputString = "%s's top tracks%s: %s"
                if period != None:
                    if period not in ('0', '3', '6', '12', 'w'):
                        username = period
                        period = None
                        
                if username is None:
                    username = msg.nick
                    if not db.hasRecord(msg.nick):
                        raise LastFMUsernameNotSetError
                userRef = network.get_user(getLastFMUsername(username))
                
                pPeriod = None
                durationText = ""
                if period == None or period == '0':
                    pPeriod = pylast.PERIOD_OVERALL
                    durationText = " of all time"
                if period == 'w':
                    pPeriod = pylast.PERIOD_7DAYS
                    durationText = " of the past week"
                if period == '3':
                    pPeriod = pylast.PERIOD_3MONTHS
                    durationText = " of the past 3 months"
                if period == '6':
                    pPeriod = pylast.PERIOD_6MONTHS
                    durationText = " of the past 6 months"
                if period == '12':
                    pPeriod = pylast.PERIOD_12MONTHS
                    durationText = " of the past year"
                if pPeriod == None:
                    raise IncorrectPeriodError
                topTracks = userRef.get_top_tracks(pPeriod)
                if len(topTracks) > 8:
                    topTracks = topTracks[:8]
                topTracksTexts = commaAndify(["" 
                    + x.item.get_artist().get_name() + " - " 
                    + x.item.get_name()  + " (" + x.weight + " play"
                    + ("" if x.weight == "1" else "s") + ")"
                    for x in topTracks])
                output = outputString % (username, durationText, topTracksTexts)
                irc.reply(output.encode("utf-8"))
            except IncorrectPeriodError:
                irc.error("The period specified must be either 3, 6, or 12.")
            except LastFMUsernameNotSetError:
                irc.error("Set your Last.FM nick first using setusername.")
            except pylast.WSError, e:
                irc.error(str(e))
        tracks = wrap(tracks, [optional('something'), optional('something')])
        
        def tags(self, irc, msg, args, username):
            """[<nick>|<Last.FM username>]
            
            Returns some info on the user's top tags."""
            try:
                outputString = "%s's top tags: %s"
                if username is None:
                    username = msg.nick
                    if not db.hasRecord(msg.nick):
                        raise LastFMUsernameNotSetError
                userRef = network.get_user(getLastFMUsername(username))
                topTags = userRef.get_top_tags(limit=12)
                topTagsTexts = commaAndify(["" + x.item.get_name() 
                    + " (" + x.weight + " use"
                    + ("" if x.weight == "1" else "s") + ")"
                    for x in topTags]).encode("utf-8")
                output = outputString % (username, topTagsTexts)
                irc.reply(output.encode("utf-8"))
            except LastFMUsernameNotSetError:
                irc.error("Set your Last.FM nick first using setusername.")
            except pylast.WSError, e:
                irc.error(str(e))
        tags = wrap(tags, [optional('something')])
    
    class rec(callbacks.Commands):
        def rec(self, irc, msg, args, username, data):
            """<nick> <artist> [because <reason>]
            
            Recommend <artist> to <nick>."""
            try:
                if username is None:
                    username = msg.nick
                    if not db.hasRecord(msg.nick):
                        raise LastFMUsernameNotSetError
                rec = Recommendation(msg.nick, username, data)
                db.addRec(username, rec)
                irc.replySuccess()
            except LastFMUsernameNotSetError:
                irc.error("That person is not in my database.")
            except pylast.WSError, e:
                irc.error(str(e))
        rec = wrap(rec, ['nick', 'text'])
        
        def get(self, irc, msg, args):
            """takes no arguments
            
            Retrieve your recommendations."""
            try:
                outputString = "Your recommendations: %s."
                if not db.hasRecord(msg.nick):
                    raise LastFMUsernameNotSetError
                recs = db.getRecs(msg.nick)
                if recs == None:
                    irc.reply("You have no recommendations.")
                else:
                    recsText = commaAndify([ircutils.bold(rec.sender)
                        + " recommends " + rec.data for rec in recs]).encode("utf-8")
                    output = outputString % recsText
                    irc.reply(output.encode("utf-8"))
            except LastFMUsernameNotSetError:
                irc.error("Set your Last.FM nick first using setusername.")
            except pylast.WSError, e:
                irc.error(str(e))
        get = wrap(get)
        
        def clear(self, irc, msg, args):
            """takes no arguments
            
            Clears all recommendations."""
            try:
                if not db.hasRecord(msg.nick):
                    raise LastFMUsernameNotSetError
                db.clearRecs(msg.nick)
                irc.replySuccess()
            except LastFMUsernameNotSetError:
                irc.error("Set your Last.FM nick first using setusername.")
            except pylast.WSError, e:
                irc.error(str(e))

Class = LastFM


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
