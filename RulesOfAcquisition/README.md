# RulesOfAcquisition

Looks up Ferengi Rules of Acquisition from Star Trek by number or keyword,
and returns a random rule when called with no arguments.

The Rules of Acquisition are a numbered series of aphorisms, guidelines, and
principles that form the foundation of business philosophy in Ferengi culture.
First written ten thousand years ago by Gint, the first Grand Nagus. The plugin
contains all 52 canon rules sourced from Memory Alpha:
https://memory-alpha.fandom.com/wiki/Rules_of_Acquisition

## Commands

### `rule [<number> | <search term>]`

Returns a Rule of Acquisition. With no argument, a random rule is returned.
When given a number, returns that specific rule (or an error if it does not
exist). When given a search term that matches multiple rules, returns a random
one of those matches.

```
<Hoaas> !rule
<Bot> Rule of Acquisition #10: Greed is eternal.

<Hoaas> !rule 1
<Bot> Rule of Acquisition #1: Once you have their money, you never give it back.

<Hoaas> !rule greed
<Bot> Rule of Acquisition #10: Greed is eternal.

<Hoaas> !rule latinum
<Bot> Rule of Acquisition #75: Home is where the heart is, but the stars are made of latinum.

<Hoaas> !rule 999
<Bot> 404 - Rule not found.
```

## Installation

```bash
pip install ./RulesOfAcquisition/
```

Then load the plugin in your Limnoria bot:

```
/msg bot load RulesOfAcquisition
```
