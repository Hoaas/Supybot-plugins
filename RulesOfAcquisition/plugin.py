# coding=utf8
###
# Copyright (c) 2012, Terje Hoås
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

import random
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('RulesOfAcquisition')

@internationalizeDocstring
class RulesOfAcquisition(callbacks.Plugin):
    """Add the help for "@plugin help RulesOfAcquisition" here
    This should describe *how* to use this plugin."""
    pass

    def rule(self, irc, msg, args, rule):
        """[number | search term]

        Returns a Rule of Acquisition (aphorisms, guidelines and principles that
        provides the foundation of business in Ferengi culture).

        No arguments return a random rule. A search term with several hits
        return a random one of those."""
        hits = None # List to store hits in, in case of search
        if rule:
            # If no argument, pick something at random.
            try:
                # If there is input, check if the string is digit.
                if rule.isdigit():
                    rule = str(rule)
                else:
                    # If input is text, raise exception
                    raise
            except:
                # Incase string input that is not digit.
                # This is a bit dirty. makes us have to loop through it twice.
                hits = []
                for r in rules:
                    if rule.lower() in r[1].lower():
                        hits.append(r)
                if len(hits) > 0:
                    rule = hits[random.randint(0, len(hits)-1)][0]
        else: # if not rule
            rule = rules[random.randint(0, len(rules)-1)][0]
        #extrahits = ""
        #if hits and len(hits) > 1:
        #    extrahits = " (" + str(len(hits)-1) + " additional hits.)"
        for r in rules:
            if str(r[0]) == str(rule):
                if str(r[0]).isdigit(): #Ohgod, the horror
                    irc.reply("Rule #{0}: {1}".format(r[0], r[1])) # + " (" + r[2] + ")")
                else:
                    irc.reply("Rule #??: {0}".format(r[1]))
                return
        irc.reply("404 - Rule not found.")
    rule = wrap(rule, [optional('text')])

rules = [
    [1, 'Once you have their money, you never give it back.', 'DS9: "The Nagus", "Heart of Stone"'],
    [3, 'Never spend more for an acquisition than you have to.', 'DS9: "The Maquis, Part II"'],
    [6, 'Never allow family to stand in the way of opportunity.', 'DS9: "The Nagus"; ENT: "Acquisition"'],
    [7, 'Keep your ears open.', 'DS9: "In the Hands of the Prophets"'],
    [9, 'Opportunity plus instinct equals profit.', 'DS9: "The Storyteller"'],
    [10, 'Greed is eternal.', 'DS9: "Prophet Motive"; VOY: "False Profits"'],
    [16, 'A deal is a deal.' , 'DS9: "Melora"'],
    [17, 'A contract is a contract is a contract ... but only between Ferengi.', 'DS9: "Body Parts"'],
    [18, 'A Ferengi without profit is no Ferengi at all.', 'DS9: "Heart of Stone"'],
    [21, 'Never place friendship above profit.', 'DS9: "Rules of Acquisition"'],
    [22, 'A wise man can hear profit in the wind.', 'DS9: "Rules of Acquisition"; VOY: "False Profits"'],
    [23, 'Nothing is more important than your health ... except for your money.', 'ENT: "Acquisition"'],
    [31, "Never make fun of a Ferengi's mother." , 'DS9: "The Siege"'],
    [33, 'It never hurts to suck up to the boss.' , 'DS9: "Rules of Acquisition", "The Dogs of War"'],
    [34, 'War is good for business', 'DS9: "Destiny", "The Siege of AR-558"'],
    [35, 'Peace is good for business.' , 'TNG: "The Perfect Mate"; DS9: "Destiny"'],
    [45, 'Expand or die.', 'ENT: "Acquisition" VOY: "False Profits"'],
    [47, 'Never trust a man wearing a better suit than your own.', 'DS9: "Rivals"'],
    [48, 'The bigger the smile, the sharper the knife.', 'DS9: "Rules of Acquisition"'],
    [57, 'Good customers are as rare as latinum. Treasure them.', 'DS9: "Armageddon Game"'],
    [59, 'Free advice is seldom cheap.', 'DS9: "Rules of Acquisition"'],
    [62, 'The riskier the road, the greater the profit.', 'DS9: "Rules of Acquisition", "Little Green Men", "Business as Usual"'],
    [74, 'Knowledge equals profit.', 'VOY: "Inside Man"'],
    [75, 'Home is where the heart is, but the stars are made of latinum.', 'DS9: "Civil Defense"'],
    [76, 'Every once in a while, declare peace. It confuses the hell out of your enemies.', 'DS9: "The Homecoming"'],
    [94, "Females and finances don't mix.", 'DS9: "Ferengi Love Songs", "Profit and Lace"'],
    [95, 'Expand or die.', 'VOY: "False Profits"; ENT: "Acquisition"'],
    [98, 'Every man has his price.', 'DS9: "In the Pale Moonlight"'],
    [102, 'Nature decays, but latinum lasts forever.', 'DS9: "The Jem\'Hadar"'],
    [103, 'Sleep can interfere with... (This rule was interrupted before it could be finished.)', 'DS9: "Rules of Acquisition"'],
    [109, 'Dignity and an empty sack is worth the sack.', 'DS9: "Rivals"'],
    [111, 'Treat people in your debt like family ... exploit them.', 'DS9: "Past Tense, Part I", "The Darkness and the Light"'],
    [112, "Never have sex with the boss's sister.", 'DS9: "Playing God"'],
    [125, "You can't make a deal if you're dead.", 'DS9: "The Siege of AR-558"'],
    [139, 'Wives serve, brothers inherit.', 'DS9: "Necessary Evil"'],
    [168, 'Whisper your way to success.', 'DS9: "Treachery, Faith and the Great River"'],
    ['-', 'A man is only worth the sum of his possessions.', 'ENT: "Acquisition"'],
    [190, 'Hear all, trust nothing.', 'DS9: "Call to Arms"'],
    [194, "It's always good to know about new customers before they walk in your door.", 'DS9: "Whispers"'],
    [203, 'New customers are like razor-toothed gree-worms. They can be succulent, but sometimes they bite back.', 'DS9: "Little Green Men"'],
    [208, 'Sometimes the only thing more dangerous than a question is an answer.', 'DS9: "Ferengi Love Songs"'],
    [211, "Employees are the rungs on the ladder of success. Don't hesitate to step on them.", 'DS9: "Bar Association"'],
    [214, 'Never begin a negotiation on an empty stomach.', 'DS9: "The Maquis, Part I"'],
    [217, "You can't free a fish from water.", 'DS9: "Past Tense, Part I"'],
    [223, '(incomplete, but presumably concerned the relationship between "keeping busy" and "being successful")', 'DS9: "Profit and Loss"'],
    [229, 'Latinum lasts longer than lust.', 'DS9: "Ferengi Love Songs"'],
    [239, 'Never be afraid to mislabel a product.', 'DS9: "Body Parts"'],
    [263, 'Never allow doubt to tarnish your lust for latinum.', 'DS9: "Bar Association"'],
    [285, 'No good deed ever goes unpunished.', 'DS9: "The Collaborator", "The Sound of Her Voice"']
]

Class = RulesOfAcquisition


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
