Automatically shortens URLs above a configurable length threshold using the
[is.gd](https://is.gd) API, posting the shortened URL back to the channel.

> **Note:** This plugin may overlap with Limnoria's built-in
> [ShrinkUrl](https://github.com/ProgVal/Limnoria/tree/master/plugins/ShrinkUrl)
> plugin, which supports multiple shortening services. Consider using that
> instead for new deployments.

## Configuration

- `supybot.plugins.UrlShortener.length` (default: `170`) — minimum URL length
  (in characters) before shortening is triggered, configurable per channel.
