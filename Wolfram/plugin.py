from supybot.commands import *
import supybot.callbacks as callbacks

import urllib
from xml.etree import ElementTree

class Wolfram(callbacks.Privmsg):

    def alpha(self, irc, msg, args, question):
        """Ask Mr. Wolfram a question, get an "answer"...maybe? It uses the
        Wolfram Alpha API.
        <http://products.wolframalpha.com/docs/WolframAlpha-API-Reference.pdf>
        """
        apikey = self.registryValue('apikey')
        if not apikey or apikey == "Not set":
            irc.reply("API key not set. see 'config help supybot.plugins.Wolfram.apikey'.")
            return

        u = "http://api.wolframalpha.com/v2/query?"
        q = urllib.urlencode({'input': question, 'appid': apikey})
        xml = urllib.urlopen(u + q).read()
        tree = ElementTree.fromstring(xml)

        if tree.attrib['success'] == "false":
            for results in tree.findall('.//error'):
                for err in results.findall('.//msg'):
                    irc.reply("Error: " + err.text)
            return

        found = False
	maxoutput = 2
	outputcount = 0
        for pod in tree.findall('.//pod'):
            title = pod.attrib['title']
            for plaintext in pod.findall('.//plaintext'):
                if plaintext.text:
                    found = True
                    """if(title == "Input interpretation" or 
                    title == "Result" or 
                    title == "Input" or 
                    title == "Exact result" or 
                    title == "Decimal approximation"):
                    """
                    if outputcount < maxoutput:
                        output = plaintext.text
                        output = output.replace(' | ', ': ')
                        output = output.replace('\n', ', ')
                        irc.reply(("%s: %s" % (title, output.encode('utf-8'))))
                        outputcount += 1
        if not found:
            irc.reply("huh, I dunno, I'm still a baby AI. Wait till the singularity I guess?")

    alpha = wrap(alpha, ['text'])


Class = Wolfram
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
