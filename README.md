#SongDB

SongDB indexes your music collection (CDs, files, whatever) and makes it all searchable on various attributes through a web interface.

[![songdb](songdb_mini.png?raw=true)](songdb.png?raw=true)

Requires Python 2.7+. Tested on Linux and Windows. Should work in all modern browsers.

SongDB uses SQLite3 as a database backend and provides a REST/JSON API using Flask. The web interface uses JQuery. The database model is a star schema, each attribute has its own dimension table. This makes searching fast end efficient.

I wrote this for a friend in a bit of a hurry. The code is pretty raw and tailored for a specific need. I did not have time to make a test suite, but I've not heard of any bugs as of yet. Fingers crossed ;)

##Attributes

These attributes are indexed (all attributes are optional):

Attribute    | Type
------------ | ----
track        | integer
title        | text
length       | integer
artist       | text
albumartist  | text
composer     | text
performer    | text
album        | text
date         | text
genre        | text
codec        | text
bitrate      | integer
codecprofile | text
bitdepth     | integer
samplerate   | integer
channels     | integer
tool         | text
comment      | text
note         | text
path         | text
modified     | date/time (yyyy-mm-dd hh:mm:ss)

##License

MIT

##Installation

Prerequisites:
* Python 2.7+
* pip


1. Install dependencies

    ```
    pip install -r requirements.txt
    ```
2. Copy songdb directory to a directory of your choice
3. Set configuration options in songdb/config.cfg
4. Start SongDB

    ```
    python server.py
    ```
    (on Windows it can be run as a background process using pythonw instead of python)
5. Open your browser and go to http://localhost:3333 or whatever host/port you've configured

##Loading your music

The SQLite database is populated on startup from text files placed in the configured _datadir_. These text files must all have the same encoding. For example utf8, see configuration option _encoding_. The text files can be gzipped to save disk space.
Any number of text files can be placed in the datadir. Each text file must abide by the following format. A hypen character (-) is used to separate songs.
(Note: only a subset of available attributes are set in this example. See list above for all available attributes)
```
-
track:01
title:Bags' Groove (Take 1)
length:678
artist:Miles Davis & The Modern Jazz Giants
albumartist:Miles Davis & The Modern Jazz Giants
album:Bags' Groove
date:1954
genre:Hard Bop
codec:CDDA
bitdepth:16
samplerate:44100
channels:2
-
track:02
title:Bags' Groove (Take 2)
length:565
artist:Miles Davis & The Modern Jazz Giants
albumartist:Miles Davis & The Modern Jazz Giants
album:Bags' Groove
date:1954
genre:Hard Bop
codec:CDDA
bitdepth:16
samplerate:44100
channels:2
-
track:03
title:Airegin
length:301
artist:Miles Davis & The Modern Jazz Giants
albumartist:Miles Davis & The Modern Jazz Giants
album:Bags' Groove
date:1954
genre:Hard Bop
codec:CDDA
bitdepth:16
samplerate:44100
channels:2
-
```
