# AGENTS.md — Supybot-plugins Development Guide

This repository contains IRC bot plugins for [Limnoria](https://github.com/ProgVal/Limnoria),
a fork of Supybot. All plugins are written in **Python 3** only; there is no Python 2
compatibility requirement. The official plugin developer docs are at
https://docs.limnoria.net/develop/index.html

---

## Running Tests

Limnoria ships its own test runner — do **not** use `pytest` or `python -m unittest` directly.

```bash
# Run all tests for a single plugin
limnoria-test PluginName/

# Run tests for multiple plugins
limnoria-test PluginName/ OtherPlugin/

# Run a single test method
limnoria-test PluginName/ -k testMethodName

# Run all plugins in the repo (from the repo root)
limnoria-test */
```

Install Limnoria via pip (`pip install limnoria`) to get the `limnoria-test` command.

---

## Installation

Each plugin has a `pyproject.toml` and can be installed as a pip package
directly from the local directory — no PyPI publishing required:

```bash
pip install ./PluginName/
```

Or directly from GitHub without cloning:

```bash
pip install "limnoria-pluginname @ git+https://github.com/Hoaas/Supybot-plugins.git#subdirectory=PluginName"
```

The `pyproject.toml` registers the plugin via the `limnoria.plugins` entry
point, so Limnoria auto-discovers it after installation without needing to
manually configure a plugin directory.

When creating a new plugin, copy the `pyproject.toml` from an existing plugin
and update the `name`, `authors`, entry point key, and package name fields.
The pip package name convention is `limnoria-<pluginname>` (all lowercase).

---

## Plugin Structure

Each plugin lives in its own directory. Required files:

```
PluginName/
├── __init__.py      # Module bootstrap — load config, plugin, and test
├── plugin.py        # Main plugin logic — the Plugin class
├── config.py        # Registry configuration variables
├── test.py          # Test cases (PluginTestCase subclass)
├── README.md        # User-facing documentation
└── pyproject.toml   # Package metadata for pip installation
```

### `__init__.py` boilerplate

```python
import supybot
import supybot.world as world

__version__ = ""
__author__ = supybot.Author('Terje Hoås', 'Hoaas', 'terje@robogoat.dev')
__contributors__ = {}
__url__ = ''

from . import config
from . import plugin
from importlib import reload
reload(config)
reload(plugin)

if world.testing:
    from . import test

Class = plugin.Class
configure = config.configure
```

### `plugin.py` structure

```python
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('PluginName')
except ImportError:
    _ = lambda x: x


def formatResult(item):
    """Module-level helper — pure logic, no bot dependency."""
    return f'{item["name"]}: {item["value"]}'


class PluginName(callbacks.Plugin):
    """Plugin docstring shown to users with 'help PluginName'."""
    threaded = True

    @wrap(['text'])
    def mycommand(self, irc, msg, args, text):
        """<text>

        Description shown by the 'help' command.
        """
        data = utils.web.getUrl(f'https://example.com/api?q={text}').decode()
        result = formatResult(json.loads(data))
        irc.reply(result)

Class = PluginName   # Always the last line — required by Supybot
```

### Command architecture

Keep command methods **thin**: fetch data, call a helper, reply. Extract all
non-trivial logic (parsing, filtering, formatting) into **module-level helper
functions**. This makes the logic testable without a running bot or network.

---

## Code Style

### Formatting

Indentation, line length, charset, and whitespace are defined in `.editorconfig`
at the repo root — any editor with EditorConfig support will apply these
automatically. Do **not** add vim modelines or `# coding=utf8` headers.

Follow [PEP 8](https://peps.python.org/pep-0008/) except where noted below.

### Imports

Standard library imports come first, then supybot imports. Prefer the
explicit `import supybot.X as X` form, or the compact `from supybot import X, Y`
form for multiple supybot modules. Import order within each group should be by
string length (Limnoria convention):

```python
import json
import urllib.error

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
```

Always wrap the i18n import in a try/except at module level:

```python
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('PluginName')
except ImportError:
    _ = lambda x: x
```

### String formatting

Prefer f-strings. Avoid `+` concatenation for more than two strings, and use only `%s` (not `%d`, `%f`) in format strings unless float precision is needed.

### Naming conventions

| Thing | Style |
|---|---|
| Methods and functions | `camelCase` |
| Variables | `camelCase` |
| Classes | `PascalCase` |
| Config registry keys | `camelCase` |
| SQL keywords | `ALL CAPS` |
| SQL table names | `lower_with_underscores` |

Common Limnoria variable name conventions: `irc` (Irc object), `msg` (IrcMsg),
`channel` (channel string), `nick` (nick string), `db` (database handle),
`fd` (file-like object).

---

## Plugin Conventions

### Commands

Every command method must:
1. Have a docstring with the argument list on the first line, blank line, then description.
2. Be registered with `@wrap([...])` (preferred decorator form) or the older
   `command = wrap(command, [...])` assignment form.
3. Use `threaded = True` at the class level (set it on every plugin).

Common `wrap` converters: `'text'`, `'int'`, `'anything'`, `'url'`,
`'somethingWithoutSpaces'`, `'channel'`, `optional('text')`, `additional('text')`,
`getopts({'flag': 'type'})`.

### HTTP fetching

Always use Limnoria's built-in utility — never import `requests` or use
`urllib.request` directly for fetching:

```python
data = utils.web.getUrl(url).decode()
data = utils.web.getUrl(url, headers={'Accept': 'application/json'}).decode()
```

For APIs returning JSON: `json.loads(utils.web.getUrl(url).decode())`.

### Configuration

Read config values via `self.registryValue('key')` (global) or
`self.registryValue('key', channel)` (per-channel). Check for unset API keys:

```python
apikey = self.registryValue('apikey')
if not apikey or apikey == 'Not set':
    irc.reply("API key not set. See 'config help supybot.plugins.PluginName.apikey'.")
    return
```

### IRC formatting

Use `ircutils.bold(text)`, `ircutils.mircColor(text, 'Red')`, or `ircutils.mircColor(text, 12)` for IRC text formatting.

### Timezones

Always use timezone-aware datetimes. Comparing an aware datetime to a naive
one raises a `TypeError` at runtime in Python 3.

```python
from datetime import datetime, timezone

# Bad — naive, will crash if compared to an aware datetime
now = datetime.now()

# Good — aware
now = datetime.now(timezone.utc)
```

Keep `tzinfo` throughout your code; don't strip it with `.replace(tzinfo=None)`
unless you are certain all datetimes in the comparison are naive.

---

## Error Handling

- Catch specific exceptions; avoid bare `except:`.
- Report user-facing errors with `irc.reply(...)` or `irc.error(...)`.
- Use `self.log.*` for internal logging — never `print()`.
- Log level guidance:
  - `self.log.debug(...)` — implementation details, debugging printfs (leave in code, commented out).
  - `self.log.info(...)` — what the plugin is doing (not critical, just informative).
  - `self.log.warning(...)` — something the operator should notice.
  - `self.log.error(...)` — something went wrong; uncaught exceptions.
- Pass format parameters as separate arguments to the logger (do not use `%`):
  ```python
  self.log.debug('Fetching URL: %s', url)   # Good
  self.log.debug('Fetching URL: %s' % url)  # Bad
  ```
- Close file descriptors and sockets explicitly; use try/finally:
  ```python
  fd = urllib.request.urlopen(url)
  try:
      s = fd.read()
  finally:
      fd.close()
  ```

---

## Internationalisation (i18n)

Only add i18n if the plugin has meaningful user-visible strings worth
translating (error messages, formatted output, docstrings). If the plugin
simply proxies raw data from an external source with no plugin-authored
strings, skip i18n.

### Standard setup

Update the i18n import to also import `internationalizeDocstring`:

```python
try:
    from supybot.i18n import (PluginInternationalization,
                              internationalizeDocstring)
    _ = PluginInternationalization('PluginName')
except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f
```

Add `@internationalizeDocstring` to each command method — place it **between**
`@wrap([...])` and `def`, not above `@wrap`:

```python
@wrap(['text'])
@internationalizeDocstring
def mycommand(self, irc, msg, args, text):
    ...
```

Wrap every user-visible string with `_()`. This includes error messages and
`irc.reply()` strings, but **not** data coming from APIs.

### `.po` files

Write `locales/en.po` as the source language file. The `msgid` is the English
string from source; `msgstr` is also English (may improve wording or translate
argument names in docstrings).

```po
msgid ""
msgstr ""
"Project-Id-Version: Limnoria\n"
"Language: en\n"
"Content-Type: text/plain; charset=UTF-8\n"

#: plugin.py
msgid "No results found"
msgstr "No results found"
```

For docstrings, the `msgid` must match what Limnoria's `normalize()` produces:
newlines collapsed to spaces except `\n\n` paragraph breaks, leading/trailing
whitespace stripped:

```po
msgid "<location>\n\nShows water temperatures for locations around Norway."
msgstr "<location>\n\nShows water temperatures for locations around Norway."
```

The `pyproject.toml` should include `"locales/*.po"` in `package_data`.

### Norwegian language support

`supybot.language` only accepts `de`, `en`, `es`, `fi`, `fr`, `it`, `ru` —
Norwegian (`no`) is rejected by the validator. To support `no`, use a
call-time translation wrapper instead of the bare `PluginInternationalization`
instance, and add a per-plugin `language` config var.

**`config.py`** — add alongside other config vars:

```python
conf.registerGlobalValue(PluginName, 'language', registry.String('', """Override
    the language for this plugin. Leave empty to use the global
    supybot.language setting. Accepts any locale code with a matching .po
    file, including 'no' (Norwegian)."""))
```

**`plugin.py`** — replace the standard i18n block with:

```python
try:
    import supybot.i18n as _i18n
    from supybot.i18n import PluginInternationalization, internationalizeDocstring
    _i18nInstance = PluginInternationalization('PluginName')

    def _(s):
        import supybot.conf as _conf
        try:
            lang = _conf.supybot.plugins.PluginName.language()
        except Exception:
            lang = ''
        lang = lang or _i18n.currentLocale
        if _i18nInstance.currentLocaleName != lang:
            _i18nInstance.loadLocale(lang)
        return _i18nInstance(s)

except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f
```

`internationalizeDocstring` still works correctly because it calls
`plugin_module._.__call__(docstring)` — the wrapper `_` is callable.

Write `locales/no.po` with Norwegian translations. To activate on a live bot:

```
config supybot.plugins.PluginName.language no
```

---

## Writing Tests

Limnoria provides `supybot.test.PluginTestCase` and
`supybot.test.ChannelPluginTestCase`. Use `ChannelPluginTestCase` when the
command must run inside a channel context.

Both inherit from `unittest.TestCase`, so standard unittest conventions apply.

### Two-class pattern

Each plugin's `test.py` should have two test classes:

**Class 1: `PluginNameHelperTestCase(SupyTestCase)`** — tests extracted
module-level helper functions directly. No bot, no network, no mocking needed.
Use small builder helpers to construct fixture data cleanly. Cover: happy path,
no match, case insensitivity, stale/old data filtered, malformed/missing fields
skipped, multiple results.

**Class 2: `PluginNameCommandTestCase(PluginTestCase)`** — tests the full bot
command with `utils.web.getUrl` monkey-patched. Use English strings in
assertions (tests run in the default `en` locale).

```python
from supybot.test import *
import supybot.utils as utils


def makeEntry(name='Oslo', temp=18.5):
    """Builder helper for fixture data."""
    return {'name': name, 'temp': temp}


class WeatherHelperTestCase(SupyTestCase):

    def testFindWeather(self):
        data = [makeEntry('Oslo'), makeEntry('Bergen')]
        self.assertEqual(findWeather(data, 'oslo')[0]['name'], 'Oslo')

    def testFindWeatherNoMatch(self):
        self.assertEqual(findWeather([], 'Oslo'), [])

    def testFormatWeather(self):
        self.assertEqual(formatWeather(makeEntry()), 'Oslo: 18.5°C')


class WeatherCommandTestCase(PluginTestCase):
    plugins = ('Weather',)

    def testWeather(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: b'[{"name":"Oslo","temp":18.5}]'
        try:
            self.assertResponse('weather Oslo', 'Oslo: 18.5°C')
        finally:
            utils.web.getUrl = original

    def testWeatherNotFound(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: b'[]'
        try:
            self.assertResponse('weather Nowhere', 'No results found.')
        finally:
            utils.web.getUrl = original
```

### Plugins requiring API keys

Set a fake key at the test class level so the key-check passes before the
mocked fetch is called:

```python
class OMDbCommandTestCase(PluginTestCase):
    plugins = ('OMDb',)
    config = {'supybot.plugins.OMDb.apikey': 'testkey'}

    def testMovie(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: b'{"Title":"Dune","Year":"2021"}'
        try:
            self.assertResponse('movie Dune', 'Dune (2021)')
        finally:
            utils.web.getUrl = original
```

### Key test assertions

| Method | Purpose |
|---|---|
| `assertResponse(query, expected)` | Bot reply equals `expected` |
| `assertNotError(query)` | Bot replies without an error |
| `assertError(query)` | Bot replies with an error |
| `assertRegexp(query, regexp)` | Reply matches regexp (case-insensitive by default) |
| `assertNotRegexp(query, regexp)` | Reply does not match regexp |
| `assertHelp(query)` | Command returns its help text |
| `assertAction(query, expected=None)` | Reply is a `/me` action |
| `assertActionRegexp(query, regexp)` | `/me` action matching regexp |
| `getMsg(query)` | Send command and return the raw `IrcMsg` |
| `feedMsg(query, to=None, frm=None)` | Send message without asserting anything |

Every command in a plugin **must have a docstring** — `PluginTestCase` checks
this automatically.
