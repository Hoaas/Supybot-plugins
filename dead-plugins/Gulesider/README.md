# Gulesider

Looks up names and phone numbers in the Norwegian directory [gulesider.no](https://www.gulesider.no).

## Commands

- `tlf <name>` — look up a person by name; returns phone number and address.
- `tlf <number>` — look up a phone number; returns name and address. Also checks a local copy of `nummerliste.txt` from [telefonterror.no](https://www.telefonterror.no) if present in the plugin directory.

## Optional: telefonterror.no support

Download `nummerliste.txt` from telefonterror.no and place it in the plugin directory for extended number identification.

## Notes

The gulesider.no website structure may change without notice, breaking HTML parsing. This plugin depends on `beautifulsoup4` and `lxml` for parsing.
