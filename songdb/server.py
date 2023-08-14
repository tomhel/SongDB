# coding=utf-8

"""
MIT License

Copyright (c) 2016 Tommy Hellstrom

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from functools import wraps
from flask import Flask, request, jsonify, Response
import os
import fnmatch
import logging
import logging.config
import sqlite3
from datetime import datetime
import codecs
import tempfile
import gzip
import json
import sys
import time
import threading

app = Flask(__name__, static_url_path='/static')
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False
app.config["JSON_AS_ASCII"] = False

server_conf = None
data_error = False


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


def expand_keywords(kw):
    kw_list = []

    for k in kw:
        for op, dbop, func in zip(k[1], k[2], k[3]):
            kw_list.append(("%s%s" % (k[0], op), dbop, func, k[4], k[5], k[6], k[7]))

    return kw_list


text_funcs = [
    lambda x: "%" + x.strip().replace(" ", "%") + "%",
    lambda x: "%" + x.strip().replace(" ", "%") + "%",
    lambda x: x.strip()
]

int_funcs = [
    lambda x: int(x.strip()),
    lambda x: int(x.strip()),
    lambda x: int(x.strip()),
    lambda x: int(x.strip()),
    lambda x: int(x.strip())
]

date_funcs = [
    lambda x: (datetime.strptime(x.strip(), "%Y-%m-%d %H:%M:%S") - datetime(1970, 1, 1)).total_seconds(),
    lambda x: (datetime.strptime(x.strip(), "%Y-%m-%d %H:%M:%S") - datetime(1970, 1, 1)).total_seconds(),
    lambda x: (datetime.strptime(x.strip(), "%Y-%m-%d %H:%M:%S") - datetime(1970, 1, 1)).total_seconds(),
    lambda x: (datetime.strptime(x.strip(), "%Y-%m-%d %H:%M:%S") - datetime(1970, 1, 1)).total_seconds(),
    lambda x: (datetime.strptime(x.strip(), "%Y-%m-%d %H:%M:%S") - datetime(1970, 1, 1)).total_seconds()
]

keywords = [
    ("media", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("track", ["=", "<", ">", "~", ":"], ["=", "<", ">", "!=", "="], int_funcs, 
     lambda x: int(x.strip()), lambda x: x, "integer", -9223372036854775808),
    ("title", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("length", ["=", "<", ">", "~", ":"], ["=", "<", ">", "!=", "="], int_funcs, 
     lambda x: int(x.strip()), lambda x: x, "integer", -9223372036854775808),
    ("artist", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("albumartist", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("composer", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("performer", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("album", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("date", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("genre", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("codec", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("bitrate", ["=", "<", ">", "~", ":"], ["=", "<", ">", "!=", "="], int_funcs, 
     lambda x: int(x.strip()), lambda x: x, "integer", -9223372036854775808),
    ("codecprofile", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("bitdepth", ["=", "<", ">", "~", ":"], ["=", "<", ">", "!=", "="], int_funcs, 
     lambda x: int(x.strip()), lambda x: x, "integer", -9223372036854775808),
    ("samplerate", ["=", "<", ">", "~", ":"], ["=", "<", ">", "!=", "="], int_funcs, 
     lambda x: int(x.strip()), lambda x: x, "integer", -9223372036854775808),
    ("channels", ["=", "<", ">", "~", ":"], ["=", "<", ">", "!=", "="], int_funcs, 
     lambda x: int(x.strip()), lambda x: x, "integer", -9223372036854775808),
    ("tool", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("comment", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("note", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("path", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, 
     lambda x: x.strip(), lambda x: x, "text", ""),
    ("modified", ["=", "<", ">", "~", ":"], ["=", "<", ">", "!=", "="], date_funcs, 
     lambda x: (datetime.strptime(x.strip(), "%Y-%m-%d %H:%M:%S") - datetime(1970, 1, 1)).total_seconds(), 
     lambda x: datetime.utcfromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S'), "integer", -9223372036854775808)
]

keywords_dbkeys = [x[0] for x in keywords]
keywords_db = keywords
ekeywords = expand_keywords(keywords)
keywords_lookup = {k[0]: k for k in keywords}
ekeywords_lookup = {k[0]: k for k in ekeywords}


def find_files(directory, patterns):
    for root, dirs, files in os.walk(directory):
        for basename in files:
            for pattern in patterns:
                if fnmatch.fnmatch(basename, pattern):
                    filename = os.path.join(root, basename)
                    yield filename


def load_config():
    with open(sys.argv[1]) as f:
        global server_conf
        server_conf = json.load(f)


def configure_logging():
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "generic": {
                "format": "%(asctime)s %(levelname)s [%(process)d] %(name)s [%(module)s@%(lineno)d] - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "class": "logging.Formatter"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "generic",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "generic",
                "filename": server_conf["logfile"],
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 10
            }
        },
        "loggers": {
            "waitress": {
                "propagate": 0,
                "level": "WARNING",
                "handlers": ["console", "file"]
            },
            "werkzeug": {
                "propagate": 0,
                "level": "WARNING",
                "handlers": ["console", "file"]
            },
            "songdb": {
                "propagate": 0,
                "level": server_conf["loglevel"],
                "handlers": ["console", "file"]
            }
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console"]
        }
    })


def get_dbconn():
    conn = sqlite3.connect(server_conf["database"])
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=MEMORY")
    c.execute("PRAGMA synchronous=OFF")
    c.execute("PRAGMA case_sensitive_like=OFF")
    conn.commit()
    return conn


def setup_db():
    logging.getLogger(__name__).info("setup database: %s" % server_conf["database"])
    if os.path.exists(server_conf["database"]):
        logging.getLogger(__name__).info("database already exist, skipping")
        return

    conn = get_dbconn()
    c = conn.cursor()

    for k in keywords_db:
        sql = """
            create table %s_d (
               id integer primary key,
               value %s unique not null
            )
        """ % (k[0], k[6])
        logging.getLogger(__name__).debug(sql)
        c.execute(sql)

    sql = """
        create table file_d (
           id integer primary key,
           value text unique not null,
           mtime numeric not null
        )
    """
    c.execute(sql)

    sql = """
        create table song_f (
           id integer primary key,
           %s
        )
    """ % ",\n".join(["%s_id integer not null references %s_d(id)"  % (k, k) for k in keywords_dbkeys + ["file"]])
    logging.getLogger(__name__).debug(sql)
    c.execute(sql)

    sql = """
       create view v_song as select song_f.id, %s from song_f\n%s
    """ % (",\n".join(["%s_d.value as %s" % (k, k) for k in keywords_dbkeys]),
           "\n".join(["join %s_d on %s_d.id = song_f.%s_id" % (k, k, k) for k in keywords_dbkeys]))
    logging.getLogger(__name__).debug(sql)
    c.execute(sql)
    conn.commit()
    conn.close()


def load_data():
    global data_error

    try:
        load_data_internal()
        data_error = False
    except Exception:
        data_error = True
        logging.getLogger(__name__).exception("Error loading data")


def load_data_internal():
    warncount = 0
    songcount = 0
    logging.getLogger(__name__).info("loading data: %s" % server_conf["datadir"])
    conn = get_dbconn()
    loaded = set()
    c = conn.cursor()
    c.execute("select id, value, mtime from file_d")
    current = {v: (i, m) for i, v, m in c}

    for f in find_files(server_conf["datadir"], ("*.txt", "*.txt.gz")):
        media = os.path.splitext(os.path.basename(f))[0]
        fpath = os.path.relpath(os.path.normpath(f), os.path.normpath(server_conf["datadir"]))
        fmtime = os.path.getmtime(f)
        loaded.add(fpath)

        if fpath in current:
            if abs(fmtime - current[fpath][1]) <= sys.float_info.epsilon:  # equals fp
                continue
            else:
                c.execute("delete from song_f where file_id = ?", (current[fpath][0],))

        sql = """
           insert or replace into file_d (value, mtime) values (?, ?)
        """

        logging.getLogger(__name__).debug(sql)
        c.execute(sql, (fpath, fmtime))

        org_file = f
        extracted = False

        if f.endswith(".txt.gz"):
            media = os.path.splitext(media)[0]
            extracted = True
            logging.getLogger(__name__).debug("extracting file: %s" % f)
            gziptmp = tempfile.mkstemp()

            with gzip.open(f, "rb") as gzipf:
                with os.fdopen(gziptmp[0], "wb") as plainf:
                    plainf.writelines(gzipf)

            f = gziptmp[1]

        enc = server_conf["encoding"]
        logging.getLogger(__name__).info("loading file: %s, %s" % (org_file, enc))

        with codecs.open(f, "r", enc) as ff:
            lines = [x.strip().strip(u"\ufeff").strip() for x in ff.readlines()]
            lines.append("-")

        if extracted:
            logging.getLogger(__name__).debug("removing file: %s" % f)
            os.unlink(f)

        data = {}

        for x in [x.split(":", 1) for x in lines]:
            if x[0] == "":
                continue
            if x[0] == '-':
                if len(data) > 0:
                    val_list = []

                    for k in keywords_dbkeys:
                        if k == "media":
                            val = media
                            val_list.append(val)
                        else:
                            val = data[k] if k in data else None

                            if val is None or val.strip() == "":
                                val = keywords_lookup[k][7]
                            else:
                                val = keywords_lookup[k][4](val)

                            val_list.append(val)

                        sql = """
                           insert or ignore into %s_d (value) values (?)
                        """ % k
                        logging.getLogger(__name__).debug(sql)
                        logging.getLogger(__name__).debug(val)
                        c.execute(sql, [val])

                    sql = """
                       insert into song_f (%s) select %s from %s where %s
                    """ % (", ".join(["%s_id" % a for a in keywords_dbkeys + ["file"]]),
                           ", ".join(["%s_d.id" % a for a in keywords_dbkeys + ["file"]]),
                           ", ".join(["%s_d" % a for a in keywords_dbkeys + ["file"]]),
                           " and ".join(["%s_d.value = ?" % a for a in keywords_dbkeys + ["file"]]))
                    logging.getLogger(__name__).debug(sql)
                    logging.getLogger(__name__).debug(val_list)
                    c.execute(sql, val_list + [fpath])
                    conn.commit()
                    songcount += 1

                data = {}

            elif x[0] not in keywords_dbkeys:
                logging.getLogger(__name__).warning("unknown key in file (%s): %s" % (org_file, x))
                warncount += 1
            else:
                data[x[0]] = x[1]

    for x in set(current.keys()).difference(loaded):
        c.execute("delete from song_f where file_id = ?", (current[x][0],))
        c.execute("delete from file_d where value = ?", (x,))

    conn.commit()

    c.execute("select count(*) from v_song")
    loadedcount = c.fetchone()[0]
    logging.getLogger(__name__).info(
        "Indexing %d songs. Loaded %d songs with %d warnings" % (loadedcount, songcount, warncount))

    if warncount > 0:
        logging.getLogger(__name__).warning("songs loaded with %d warnings" % warncount)

    conn.close()


def fetch_song(songid):
    fields = [x for x in keywords_dbkeys]
    fields.append("id")

    sql = "select %s from v_song where " % ", ".join(fields) + "id = ?"
    logging.getLogger(__name__).debug(sql)
    logging.getLogger(__name__).debug(songid)
    conn = get_dbconn()
    c = conn.cursor()
    c.execute(sql, (songid,))
    row = c.fetchone()

    if row is None:
        return None

    result = {k: keywords_lookup[k][5](v) if k in keywords_lookup else v 
              for k, v in zip(fields, row) if k == "id" or v != keywords_lookup[k][7]}
    conn.close()
    return result


def find_songs(afilter):
    criterias = []
    filters = afilter.strip().split("\n")

    for f in [x.strip() for x in filters]:
        if len(f) == 0:
            continue

        if not f.startswith("@"):
            raise ValidationError("filter must start with @: %s" % f)

        f = f[1:]
        found = False

        for k in ekeywords:
            if f.startswith(k[0]):
                found = True
                searchstr = f[len(k[0]):].strip()

                if len(searchstr) > 0:
                    criterias.append((k[0][0:-1], k[0][-1:], searchstr))

                break

        if not found:
            raise ValidationError("unknown filter: %s" % f)

    if len(criterias) == 0:
        return []

    where, values = build_where(set(criterias))

    fields = [
        "id", "media", "album", "artist", "title", "comment", "bitrate", 
        "bitdepth", "samplerate", "channels", "length", "codec"
    ]
    sql = "select %s from v_song where " % ", ".join(fields) + where + " limit " + str(server_conf["maxresult"])
    logging.getLogger(__name__).debug(sql)
    logging.getLogger(__name__).debug(values)
    conn = get_dbconn()
    c = conn.cursor()

    result = []

    for res in c.execute(sql, values):
        result.append({k: keywords_lookup[k][5](v) if k in keywords_lookup else v 
                       for k, v in zip(fields, res) if k == "id" or v != keywords_lookup[k][7]})

    conn.close()
    return result


def build_where(conds):
    condgroups = {}

    for c in conds:
        li = condgroups.get(c[0], [])
        li.append(c)
        condgroups[c[0]] = li

    allgroups = []
    values = []

    for k in condgroups.keys():
        groups = []

        for c in condgroups[k]:
            lookup = ekeywords_lookup[c[0] + c[1]]
            groups.append(k + " " + lookup[1] + " ?")
            values.append(lookup[2](c[2]))

        expr = " and ".join(groups)
        allgroups.append("((" + expr + ") and %s != ?)" % k)
        values.append(keywords_lookup[k][7])

    return " and ".join(allgroups), values


def valid_auth(username, password):
    return username == server_conf["username"] and password == server_conf["password"]


def requires_auth(f):
    # basic auth
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization

        if not server_conf["require_auth"]:
            return f(*args, **kwargs)
        elif not auth or not valid_auth(auth.username, auth.password):
            return Response(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})
        else:
            return f(*args, **kwargs)

    return decorated


@app.route('/song', methods=['POST'])
@requires_auth
def do_search():
    logging.getLogger(__name__).debug("search")
    jsondata = request.get_json()

    if "filter" not in jsondata:
        raise ValidationError("filter is missing")

    if jsondata["filter"] is None or jsondata["filter"].strip() == "":
        return jsonify({"songs": []})

    logging.getLogger(__name__).debug(jsondata["filter"])
    result = find_songs(jsondata["filter"])
    return jsonify({"songs": result})


@app.route('/song/<int:songid>', methods=['GET'])
@requires_auth
def get_song(songid):
    logging.getLogger(__name__).debug("get song: %d" % songid)
    song = fetch_song(songid)

    if song is None:
        raise NotFoundError("song with id %d does not exist" % songid)

    return jsonify(song)


@app.route('/song/<int:songid>/<string:attribute>', methods=['GET'])
@requires_auth
def get_song_attr(songid, attribute):
    logging.getLogger(__name__).debug("get song attribute: %d, %s" % (songid, attribute))
    song = fetch_song(songid)

    if song is None:
        raise NotFoundError("song with id %d does not exist" % songid)

    if attribute not in song:
        raise NotFoundError("attribute %s not found on song: %d" % (attribute, songid))

    return jsonify({attribute: song[attribute], "id": song["id"]})


@app.route('/admin/info', methods=['GET'])
@requires_auth
def get_info():
    logging.getLogger(__name__).debug("info")
    conn = get_dbconn()
    c = conn.cursor()
    c.execute("select count(*) from v_song")
    result = {
        "loaded": c.fetchone()[0],
        "dbsize": os.path.getsize(server_conf["database"])
    }
    conn.close()
    return jsonify(result)


@app.route('/admin/keys', methods=['GET'])
@requires_auth
def get_keys():
    logging.getLogger(__name__).debug("keys")
    return jsonify({"keys": sorted([x[0] for x in keywords])})


@app.route('/admin/log', methods=['GET'])
@requires_auth
def get_log():
    logging.getLogger(__name__).debug("log")

    def generate():
        with open(server_conf["logfile"], "r") as f:
            for line in f:
                yield line

    return Response(generate(), mimetype='text/plain')


@app.route("/")
@requires_auth
def get_index():
    if data_error:
        return get_log()

    logging.getLogger(__name__).debug("index")
    return app.send_static_file("index.html")


@app.errorhandler(NotFoundError)
def not_found_error(error):
    logging.getLogger(__name__).debug("Not found: %s" % error.message)
    return create_json_error_response(404, "Not found", error.message)


@app.errorhandler(ValidationError)
def bad_request_error(error):
    logging.getLogger(__name__).debug("Bad request: %s" % error.message)
    return create_json_error_response(400, "Bad request", error.message)


@app.errorhandler(500)
def internal_error(error):
    logging.getLogger(__name__).error("Internal error: %s" % str(error))
    return create_json_error_response(500, "Internal server error", str(error))


def create_json_error_response(code, reason, description):
    message = {
        "status": code,
        "reason": reason,
        "description": description
    }
    response = jsonify(message)
    response.status_code = code
    return response


def start_development_server():
    logging.getLogger(__name__).warning("starting development server (werkzeug)")
    app.run(host=server_conf['host'], port=int(server_conf['port']), debug=False)


def start_production_server():
    logging.getLogger(__name__).info("starting production server (waitress)")
    from waitress import serve
    serve(app, host=server_conf["host"], port=int(server_conf["port"]))


def detect_data_changes():
    while True:
        time.sleep(server_conf["scandelay"])
        load_data()


def init():
    load_config()
    configure_logging()
    setup_db()
    load_data()

    if server_conf["scandelay"] > 0:
        t = threading.Thread(target=detect_data_changes, daemon=True)
        t.start()


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {os.path.basename(sys.argv[0])} <config file>")
        return
    init()
    if server_conf["backend"].lower() == "waitress":
        start_production_server()
    elif server_conf["backend"].lower() == "werkzeug":
        start_development_server()
    else:
        raise Exception(f"invalid backend: {server_conf['backend']}")


if __name__ == '__main__':
    main()
