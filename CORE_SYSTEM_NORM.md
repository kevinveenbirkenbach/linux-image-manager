# CORE SYSTEM NORM

## Idea
This ***Core System Norm*** defines interfaces and structures which software **MUST** use to comply to this software and to avoid data and software redundancies.

## Wording
The key words **“MUST”**, **“MUST NOT”**, **“REQUIRED”**, **“SHALL”**, **“SHALL NOT”**, **“SHOULD”**,
**“SHOULD NOT”**, **“RECOMMENDED”**, **“MAY”**, and **“OPTIONAL”** in the \*.md files and in the comments of the code are to be
interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).


## Structure
### Folder
The following folder structures **MUST** be used:

| Path                        | Description |
|---|---|
$HOME/Documents/certificates/ | Contains certificates to authenticate via [certificate based authentication](https://blog.couchbase.com/x-509-certificate-based-authentication/). |
| $HOME/Documents/recovery_codes/ | Contains files with recovery_codes e.g. for [Two-factor authentication](https://en.wikipedia.org/wiki/Multi-factor_authentication). |
| $HOME/Documents/identity/ | Contains files to prove the identity of the *Core System Owner* in physical live like passports. |
| $HOME/Documents/passwords/ | Contains e.g the [KeePassXC](https://keepassxc.org/) database with all *Core System Owner* passwords. |
| $HOME/Documents/repositories/ | Contains all git repositories |
| $HOME/images/ | contains os images|
