# PLAN.md — Mistral plugin cleanup notes

## Deferred items

### Helper function extraction

`get_last_messages`, `extract_response_text`, and `extract_sources` have been
extracted to module-level in `plugin.py` and are tested in `test.py` via
`MistralHelperTestCase`.

The following helpers remain as class methods because they require bot state
(`irc`, `msg`, `self.registryValue`):

- `create_context_message` — reads `self.registryValue('contextHistory')` and
  calls the module-level `get_last_messages`.  Extracting it would require
  passing the registry value explicitly; the current structure is clean enough.
- `_setup_client` / `_create_websearch_agent` — tightly coupled to the
  Mistral SDK client object and plugin configuration.

### Full command testing with mocked mistralai SDK

The `mistral` command calls the third-party `mistralai` SDK directly rather
than going through `utils.web.getUrl`.  The standard monkey-patch pattern used
elsewhere in this repo does not apply.

To test the full command path (including response parsing and source
attribution), the `MistralClient` class would need to be patched at import
time, e.g.:

```python
from unittest.mock import MagicMock, patch

class MistralCommandMockedTestCase(PluginTestCase):
    plugins = ('Mistral',)
    config = {'supybot.plugins.Mistral.apiKey': 'test'}

    def testMistralRepliesWithResponse(self):
        fake_response = _Response([_Output('message.output', content="42")])
        with patch('Mistral.plugin.MistralClient') as MockClient:
            instance = MockClient.return_value
            instance.chat.complete.return_value = ...  # or conversations.start
            self.assertResponse('mistral what is the answer', '42')
```

This requires `unittest.mock` (stdlib) and careful patching of the module
import path.  Deferred to a future task once the plugin's SDK usage stabilises.
