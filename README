Kasownik, the Warsaw Hackerspace payment & membership system
============================================================

What is it?
-----------

It's a duct-taped together central management system for management of the [Warsaw Hackerspace](https://hackerspace.pl/) administrative bullshit.

Its' current features include:

 * import of bank transfers from BRE/mBank (via screenscraping)
 * matching of transfers to members (automatic & manual)
 * calculation of any due fees of a member
 * the Judgement Engine, which analyzes the member's financial standing and any special policies applied in order to give out a final verdict on activity
 * a simple REST API for public data
 * a less simple REST API for private data, with API keys (both global and user-based)
 * integration with an LDAP directory (currently only extra data retrieval)
 * mail notification integration (a.k.a. spam your members)
 * a Bootstrap web UI which looks nice, I guess
 * it's not in PHP!

Planned features include:

 * receiving payments from PayU
 * managing LDAP user objects and Kerberos principals
 * a pluggable synchronization system for mailing lists, door locks, LDAP group membership...

Who made it?
------------

It's currently developed mostly by [q3k](https://q3k.org) with occasinal commits and bux fies by [enleth](http://enleth.com).

Is it any good?
---------------

The branch you see here is a development branch. It has tons of features, but some of them just don't work. It's currently running in a staging, read-only set up (using the legacy system's database). However, once the feature list is complete, we will roll it out.

In short: yes, maybe, kinda. But you'll have to hack on it if you want to use it for your Hackerspace, since it's a mess.

Hacking, Copying, etc.
----------------------

Feel free to fork for your space. Our code is licensed under BSD 2-Clause. Pull requests, either for the implementation at the Warsaw Hackerspace or from your own space, are very much welcome.
