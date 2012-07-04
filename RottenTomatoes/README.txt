Gets info from RottenTomatoes.com

Sadly you need an API-key. You can get one from http://developer.rottentomatoes.com. Put this in the config variable apikey for this plugin, like this:
@config supybot.plugins.RottenTomatoes.apikey yourapikeyhere

You might want to do this in a private message to keep it ... private.

Usage example:
00:58:20 <@Hoaas> !rt Dodgeball
00:58:22 <@Bunisher> Dodgeball - A True Underdog Story - Critics: 70% (Fresh). Audience: 75% (Upright). Proudly profane and splendidly silly, Dodgeball is a worthy spiritual successor to the goofball comedies of the 1980s.

12:30:36 <@Hoaas> !rt Star Wars
12:30:37 <@Bunisher> Star Wars: Episode III - Revenge of the Sith (2005) - Critics: 80% (Certified Fresh). Audience: 64% (Upright). This sixth and final installment of George Lucas' epic space opera will please die-hard fanatics and non-believers alike -- largely due to awesome digital effects and the sheer power of the mythology. Total of 34 movies found.
12:30:41 <@Hoaas> !rt 2 Star Wars
12:30:42 <@Bunisher> Star Wars: Episode IV - A New Hope (1977) - Critics: 94% (Certified Fresh). Audience: 93% (Upright). A legendarily expansive and ambitious start to the sci-fi saga, George Lucas opened our eyes to the possiblites of blockbuster filmmaking and things have never been the same. Total of 34 movies found.