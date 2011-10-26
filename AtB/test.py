# coding=utf8
###
# Copyright (c) 2011, Terje Hoås
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#		* Redistributions of source code must retain the above copyright notice,
#		  this list of conditions, and the following disclaimer.
#		* Redistributions in binary form must reproduce the above copyright notice,
#		  this list of conditions, and the following disclaimer in the
#		  documentation and/or other materials provided with the distribution.
#		* Neither the name of the author of this software nor the name of
#		  contributors to this software may be used to endorse or promote products
#		  derived from this software without specific prior written consent.
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

from supybot.test import *


class AtBTestCase(PluginTestCase):
	plugins = ('AtB',)
	def test_calcPrice(self):
		self.assertResponse('calcPrice 7 False', '160')
		self.assertResponse('calcPrice 15 False', '310')
		self.assertResponse('calcPrice 30 False', '585')
		self.assertResponse('calcPrice 60 False', '1050')
		self.assertResponse('calcPrice 90 False', '1555')
		self.assertResponse('calcPrice 180 False', '2880')


		self.assertResponse('calcPrice 7 True', '95')
		self.assertResponse('calcPrice 15 True', '185')
		self.assertResponse('calcPrice 30 True', '350')
		self.assertResponse('calcPrice 60 True', '630')
		self.assertResponse('calcPrice 90 True', '935')
		self.assertResponse('calcPrice 180 True', '1730')

