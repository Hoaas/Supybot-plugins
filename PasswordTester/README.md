Checks a password against the [Have I Been Pwned](https://haveibeenpwned.com/) Pwned Passwords API using k-anonymity, so the full password is never transmitted.

## How it works

The password is hashed with SHA-1 locally. Only the first 5 characters of the hash are sent to the API. The API returns all hashes sharing that prefix, and the bot checks locally whether the full hash is in the list. The plaintext password never leaves the machine.

## Commands

### `password <password>`

Checks whether the given password has appeared in any known data breach.

**Examples:**

```
!password hunter2
This password has been seen 18606 times in data breaches.

!password xK9#mQ2$vL
This password has not been seen in any known data breaches.
```
