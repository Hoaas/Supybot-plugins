# AutoOp

Limnoria plugin that automatically ops, halfops, or voices users on join
based on hostmask regex matching.

## How it works

When a user joins a channel, the bot checks their `nick!ident@host` against
a per-channel database of regex patterns. If a pattern matches, the
corresponding mode (op/halfop/voice) is applied — provided the bot itself
has op in the channel.

Patterns are stored in Limnoria's data directory as
`<channel>/AutoOp.db` (JSON format).

## Commands

All commands require the `owner` capability.

### `autoop [<channel>] <nick|hostmask>`

Registers a nick (resolved to their current hostmask) or a literal
hostmask/regex for automatic op on join.

### `autohalfop [<channel>] <nick|hostmask>`

Same as `autoop`, but grants halfop (`+h`).

### `autovoice [<channel>] <nick|hostmask>`

Same as `autoop`, but grants voice (`+v`).

## Notes

- Hostmask patterns are regular expressions matched against `nick!ident@host`.
- When a nick is given instead of a hostmask, dots in the resolved hostmask
  are automatically escaped so the pattern matches literally.
- The bot must have op (`+o`) in the channel to apply any modes.
- There is currently no command to list or remove entries — edit the JSON
  database file directly if needed.
