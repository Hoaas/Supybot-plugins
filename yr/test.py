###
# Copyright (c) 2010, Terje Hoaas
# All rights reserved.
#
#
###

from supybot.test import *

class TemperatureTestCase(PluginTestCase):
    plugins = ('Temperature',)

    def testSunrise(self):
        pass

#    def testRandom(self):
        # difficult to test, etc
#        self.assertNotError('random')
        
#    def testSeed(self):
#        self.assertNotError('seed 20')
        
#    def testSample(self):
#        self.assertError('sample 20 foo')
#        self.assertResponse('sample 1 foo', 'foo')
#        self.assertRegexp('sample 2 foo bar', '... and ...')
#        self.assertRegexp('sample 3 foo bar baz', '..., ..., and ...')
        
#    def testDiceRoll(self):
#        self.assertActionRegexp('diceroll', 'rolls a \d');
    
#    def testSeedActuallySeeds(self):
#        self.assertNotError('seed 20')
#        m1 = self.getMsg('random')
#        self.assertNotError('seed 20')
#        m2 = self.getMsg('random')
#        self.failUnlessEqual(m1, m2)
#        m3 = self.getMsg('random')
#        self.failIfEqual(m2, m3)
    
    
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
