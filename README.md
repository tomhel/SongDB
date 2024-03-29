# SongDB

SongDB indexes your music collection (CDs, files, whatever) and makes it all searchable on various attributes through a web interface.

[![songdb](songdb_mini.png?raw=true)](songdb.png?raw=true)

Requires Python 3+. Tested on Linux and Windows. Should work in all modern browsers.

SongDB uses SQLite3 as a database backend and provides a REST/JSON API using Flask and Waitress. The web interface uses JQuery. The database model is a star schema, each attribute has its own dimension table. This makes searching fast and efficient.

I wrote this for a friend in a bit of a hurry. The code is pretty raw and tailored for a specific need. I did not have time to make a test suite, but I've not heard of any bugs yet. Fingers crossed ;)

## License

MIT

## Attributes

These attributes are indexed (all attributes are optional):

| Attribute    | Type                            |
|--------------|---------------------------------|
| track        | integer                         |
| title        | text                            |
| length       | integer                         |
| artist       | text                            |
| albumartist  | text                            |
| composer     | text                            |
| performer    | text                            |
| album        | text                            |
| date         | text                            |
| genre        | text                            |
| codec        | text                            |
| bitrate      | integer                         |
| codecprofile | text                            |
| bitdepth     | integer                         |
| samplerate   | integer                         |
| channels     | integer                         |
| tool         | text                            |
| comment      | text                            |
| note         | text                            |
| path         | text                            |
| modified     | date/time (yyyy-mm-dd hh:mm:ss) |

## Installation

Dependencies:
* Python 3+
* Flask
* Waitress


1. Install SongDB
    ```
    cd SongDB
    pip install .
    ```
3. Set configuration options in config.json
4. Start SongDB
    ```
    songdb_server config.json
    ```
    (on Windows it can be run as a background process using pythonw)
5. Open your browser and go to http://localhost:3333 or whatever host/port you've configured

## Configuration

### Options

| Option       | Description                                                                                                                          |
|--------------|--------------------------------------------------------------------------------------------------------------------------------------|
| host         | Host to bind.                                                                                                                        |
| port         | Port to bind.                                                                                                                        |
| logfile      | Path to log file.                                                                                                                    |
| loglevel     | Loglevel, _DEBUG_, _INFO_, _WARNING_, _ERROR_.                                                                                       |
| datadir      | Path to directory for loading the music.                                                                                             |
| encoding     | Encoding of text files in _datadir_.                                                                                                 |
| database     | Path to SQLite database file.                                                                                                        |
| maxresult    | Maximum number of hits to return to the web interface in a query.                                                                    |
| username     | Username to access the web interface.                                                                                                |
| password     | Password to access the web interface.                                                                                                |
| require_auth | Enforce username and password.                                                                                                       |
| backend      | Server backend to use, waitress or werkzeug. Waitress is strongly recommended for production use. Only use werkzeug for development. |
| scandelay    | Scan interval (in seconds) for change detection of files in datadir. A value of 0 disables change detection.                         |

### Example
```json
{
    "host": "127.0.0.1",
    "port": 3333,
    "logfile": "/tmp/songdb.log",
    "loglevel": "INFO",
    "datadir": "example_data/",
    "encoding": "utf8",
    "database": "/tmp/songdb.db",
    "maxresult": 1000,
    "username": "song",
    "password": "db",
    "require_auth": false,
    "backend": "waitress",
    "scandelay": 300
}
```

## Loading your music

The SQLite database is populated on startup from text files placed in the configured _datadir_. The _datadir_ is also scanned for changes during runtime by looking at file modified time. 
The text files must all have the same encoding. For example utf8, see configuration option _encoding_. The text files can be gzipped to save disk space.
Any number of text files can be placed in the _datadir_. Each text file must abide by the following format. A hypen character (-) is used to separate songs.
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
