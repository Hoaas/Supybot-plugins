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

There is no `Makefile`, `tox.ini`, `setup.py`, or CI configuration in this repository.
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
__author__ = supybot.authors.unknown
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

class PluginName(callbacks.Plugin):
    """Plugin docstring shown to users with 'help PluginName'."""
    threaded = True

    @wrap(['text'])
    def mycommand(self, irc, msg, args, text):
        """<text>

        Description shown by the 'help' command.
        """
        irc.reply(text)

Class = PluginName   # Always the last line — required by Supybot
```

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

Prefer f-strings. Avoid string concatenation with `+` for more than two strings.

```python
# Bad
s = a + b + c
# Good
s = f'{a}{b}{c}'
```

Use only `%s` (not `%d`, `%f`) in format strings unless float precision is needed.

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

```python
ircutils.bold(text)
ircutils.mircColor(text, 'Red')   # named colour
ircutils.mircColor(text, 12)      # colour by number
```

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

## Writing Tests

Limnoria provides `supybot.test.PluginTestCase` and
`supybot.test.ChannelPluginTestCase`. Use `ChannelPluginTestCase` when the
command must run inside a channel context.

Both inherit from `unittest.TestCase`, so standard unittest conventions apply.

### Minimal `test.py`

```python
from supybot.test import *

class PluginNameTestCase(PluginTestCase):
    plugins = ('PluginName',)

    def testMyCommand(self):
        self.assertNotError('mycommand some input')

    def testMyCommandResponse(self):
        self.assertResponse('echo hello', 'hello')
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

### Setup and teardown

```python
def setUp(self):
    super().setUp()
    self.prefix = 'foo!bar@baz'
    self.feedMsg('register tester moo', to=self.nick, frm=self.prefix)
    self.getMsg(' ')   # consume the response

def tearDown(self):
    # cleanup here
    super().tearDown()
```

### Config in tests

```python
import supybot.conf as conf

class MyTestCase(PluginTestCase):
    # Set at class level:
    config = {'supybot.commands.nested': False}

    def testThing(self):
        # Set temporarily inside a test:
        with conf.supybot.commands.nested.context(False):
            self.assertNotError('mycommand')
```

### Testing helper code (non-command logic)

For unit-testing helper functions without running bot commands, subclass
`supybot.test.SupyTestCase` instead:

```python
from supybot.test import *

class MyHelperTestCase(SupyTestCase):
    def testParseResult(self):
        self.assertEqual(parseResult('foo'), 'expected')
```

Every command in a plugin **must have a docstring** — `PluginTestCase` checks
this automatically.
