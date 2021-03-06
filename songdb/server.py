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
import atexit
import sqlite3
from datetime import datetime
import codecs
import tempfile
import gzip
import sys
import ConfigParser


app = Flask(__name__, static_url_path='/static')
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False
app.config["JSON_AS_ASCII"] = False

server_conf = None
logger = None
warncount = 0
songcount = 0


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
    ("media", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("track", ["=", "<", ">", "~", ":"], ["=", "<", ">", "!=", "="], int_funcs, lambda x: int(x.strip()), lambda x: x, "integer", -9223372036854775808),
    ("title", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("length", ["=", "<", ">", "~", ":"], ["=", "<", ">", "!=", "="], int_funcs, lambda x: int(x.strip()), lambda x: x, "integer", -9223372036854775808),
    ("artist", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("albumartist", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("composer", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("performer", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("album", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("date", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("genre", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("codec", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("bitrate", ["=", "<", ">", "~", ":"], ["=", "<", ">", "!=", "="], int_funcs, lambda x: int(x.strip()), lambda x: x, "integer", -9223372036854775808),
    ("codecprofile", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("bitdepth", ["=", "<", ">", "~", ":"], ["=", "<", ">", "!=", "="], int_funcs, lambda x: int(x.strip()), lambda x: x, "integer", -9223372036854775808),
    ("samplerate", ["=", "<", ">", "~", ":"], ["=", "<", ">", "!=", "="], int_funcs, lambda x: int(x.strip()), lambda x: x, "integer", -9223372036854775808),
    ("channels", ["=", "<", ">", "~", ":"], ["=", "<", ">", "!=", "="], int_funcs, lambda x: int(x.strip()), lambda x: x, "integer", -9223372036854775808),
    ("tool", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("comment", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("note", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
    ("path", ["=", "~", ":"], ["like", "not like", "collate nocase ="], text_funcs, lambda x: x.strip(), lambda x: x, "text", ""),
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
    conf = os.path.join(os.path.dirname(sys.argv[0]), "config.cfg")
    config = ConfigParser.ConfigParser()
    config.read(conf)
    global server_conf
    server_conf = {k: v for k, v in config.items("server")}


def configure_logging():
    if server_conf["logfile"] == ":console:":
        logging.basicConfig(level=server_conf["loglevel"], format="%(asctime)-15s [%(levelname)s] %(message)s")
    else:
        logging.basicConfig(filemode="w", filename=server_conf["logfile"], level=server_conf["loglevel"], format="%(asctime)-15s [%(levelname)s] %(message)s")
    global logger
    logger = logging.getLogger("song-api")


def get_dbconn():
    conn = sqlite3.connect(server_conf["database"])
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=MEMORY")
    c.execute("PRAGMA synchronous=OFF")
    c.execute("PRAGMA case_sensitive_like=OFF")
    conn.commit()
    return conn


def setup_db():
    logger.info("setup database: %s" % server_conf["database"])
    if os.path.exists(server_conf["database"]): os.unlink(server_conf["database"])

    conn = get_dbconn()
    c = conn.cursor()

    for k in keywords_db:
        sql = """
            create table %s_d (
               id integer primary key,
               value %s unique not null
            )
        """ % (k[0], k[6])
        logger.debug(sql)
        c.execute(sql)

    sql = """
        create table song_f (
           id integer primary key,
           %s
        )
    """ % ",\n".join(["%s_id integer not null references %s_d(id)"  % (k, k) for k in keywords_dbkeys])
    logger.debug(sql)
    c.execute(sql)

    sql = """
       create view v_song as select song_f.id, %s from song_f\n%s
    """ % (",\n".join(["%s_d.value as %s" % (k, k) for k in keywords_dbkeys]),
           "\n".join(["join %s_d on %s_d.id = song_f.%s_id" % (k, k, k) for k in keywords_dbkeys]))
    logger.debug(sql)
    c.execute(sql)
    conn.commit()
    conn.close()


def load_data():
    global warncount
    global songcount
    warncount = 0
    songcount = 0
    logger.info("loading data: %s" % server_conf["datadir"])
    conn = get_dbconn()
    c = conn.cursor()

    for f in find_files(server_conf["datadir"], ("*.txt", "*.txt.gz")):
        media = os.path.splitext(os.path.basename(f))[0]
        org_file = f
        extracted = False

        if f.endswith(".txt.gz"):
            media = os.path.splitext(media)[0]
            extracted = True
            logger.debug("extracting file: %s" % f)
            gziptmp = tempfile.mkstemp()

            with gzip.open(f, "rb") as gzipf:
                with os.fdopen(gziptmp[0], "wb") as plainf:
                    plainf.writelines(gzipf)

            f = gziptmp[1]

        enc = server_conf["encoding"]
        logger.info("loading file: %s, %s" % (org_file, enc))

        with codecs.open(f, "r", enc) as ff:
            lines = [x.strip().strip(u"\ufeff").strip() for x in ff.readlines()]
            lines.append("-")

        if extracted:
            logger.debug("removing file: %s" % f)
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
                        logger.debug(sql)
                        logger.debug(val)
                        c.execute(sql, [val])

                    sql = """
                       insert into song_f (%s) select %s from %s where %s
                    """ % (", ".join(["%s_id" % a for a in keywords_dbkeys]),
                           ", ".join(["%s_d.id" % a for a in keywords_dbkeys]),
                           ", ".join(["%s_d" % a for a in keywords_dbkeys]),
                           " and ".join(["%s_d.value = ?" % a for a in keywords_dbkeys]))
                    logger.debug(sql)
                    logger.debug(val_list)
                    c.execute(sql, val_list)
                    conn.commit()
                    songcount += 1

                data = {}

            elif x[0] not in keywords_dbkeys:
                logger.warn("unknown key in file (%s): %s" % (org_file, x))
                warncount += 1
            else:
                data[x[0]] = x[1]

    c.execute("select count(*) from v_song")
    loadedcount = c.fetchone()[0]
    logger.info("Found %d songs. Loaded %d songs with %d warnings" % (loadedcount, songcount, warncount))

    if loadedcount != songcount:
        logger.warn("%d songs was not loaded" % (songcount - loadedcount))

    if warncount > 0:
        logger.warn("songs loaded with %d warnings" % warncount)

    conn.close()


def fetch_song(songid):
    fields = [x for x in keywords_dbkeys]
    fields.append("id")

    sql = "select %s from v_song where " % ", ".join(fields) + "id = ?"
    logger.debug(sql)
    logger.debug(songid)
    conn = get_dbconn()
    c = conn.cursor()
    c.execute(sql, (songid,))
    row = c.fetchone()

    if row is None:
        return None

    result = {k: keywords_lookup[k][5](v) if k in keywords_lookup else v for k, v in zip(fields, row) if k == "id" or v != keywords_lookup[k][7]}
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
        "id", "media", "album", "artist", "title", "comment", "bitrate", "bitdepth", "samplerate", "channels", "length", "codec"
    ]
    sql = "select %s from v_song where " % ", ".join(fields) + where + " limit " + server_conf["maxresult"]
    logger.debug(sql)
    logger.debug(values)
    conn = get_dbconn()
    c = conn.cursor()

    result = []

    for res in c.execute(sql, values):
        result.append({k: keywords_lookup[k][5](v) if k in keywords_lookup else v for k, v in zip(fields, res) if k == "id" or v != keywords_lookup[k][7]})

    conn.close()
    return result


def build_where(conds):
    condgroups = {}

    for c in conds:
        l = condgroups.get(c[0], [])
        l.append(c)
        condgroups[c[0]] = l

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


def check_auth(username, password):
    return username == server_conf["username"] and password == server_conf["password"]


def authenticate():
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    # basic auth, based on code snippet: http://flask.pocoo.org/snippets/8/
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization

        if not str2bool(server_conf["require_auth"]):
            return f(*args, **kwargs)
        elif not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        else:
            return f(*args, **kwargs)

    return decorated


@app.route('/song', methods=['POST'])
@requires_auth
def do_search():
    logger.debug("search")
    jsondata = request.get_json()

    if "filter" not in jsondata:
        raise ValidationError("filter is missing")

    if jsondata["filter"] is None or jsondata["filter"].strip() == "":
        return jsonify({"songs": []})

    logger.debug(jsondata["filter"])
    result = find_songs(jsondata["filter"])
    return jsonify({"songs": result})


@app.route('/song/<int:songid>', methods=['GET'])
@requires_auth
def get_song(songid):
    logger.debug("get song: %d" % songid)
    song = fetch_song(songid)

    if song is None:
        raise NotFoundError("song with id %d does not exist" % songid)

    return jsonify(song)


@app.route('/song/<int:songid>/<string:attribute>', methods=['GET'])
@requires_auth
def get_song_attr(songid, attribute):
    logger.debug("get song attribute: %d, %s" % (songid, attribute))
    song = fetch_song(songid)

    if song is None:
        raise NotFoundError("song with id %d does not exist" % songid)

    if attribute not in song:
        raise NotFoundError("attribute %s not found on song: %d" % (attribute, songid))

    return jsonify({attribute: song[attribute], "id": song["id"]})


@app.route('/admin/info', methods=['GET'])
@requires_auth
def get_info():
    logger.debug("info")
    conn = get_dbconn()
    c = conn.cursor()
    c.execute("select count(*) from v_song")
    result = {
        "loaded": c.fetchone()[0],
        "found": songcount,
        "warnings": warncount,
        "dbsize": os.path.getsize(server_conf["database"])
    }
    conn.close()
    return jsonify(result)


@app.route('/admin/keys', methods=['GET'])
@requires_auth
def get_keys():
    logger.debug("keys")
    return jsonify({"keys": sorted([x[0] for x in keywords])})


@app.route('/admin/shutdown', methods=['GET'])
@requires_auth
def do_shutdown():
    logger.info("api shutdown triggered")
    shutdown_server()
    return jsonify({})


@app.route('/admin/log', methods=['GET'])
@requires_auth
def get_log():
    logger.debug("log")

    def generate():
        with open(server_conf["logfile"], "r") as f:
            for line in f:
                yield line

    return Response(generate(), mimetype='text/plain')


@app.route("/")
@requires_auth
def get_index():
    logger.debug("index")
    return app.send_static_file("index.html")


@app.errorhandler(NotFoundError)
def not_found_error(error):
    logger.debug("Not found: %s" % error.message)
    return create_json_error_response(404, "Not found", error.message)


@app.errorhandler(ValidationError)
def bad_request_error(error):
    logger.debug("Bad request: %s" % error.message)
    return create_json_error_response(400, "Bad request", error.message)


@app.errorhandler(500)
def internal_error(error):
    logger.error("Internal error: %s" % str(error))
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


def str2bool(s):
    return s.lower() in ["true"]


def remove_pid():
    if os.path.isfile(server_conf['pidfile']):
        os.unlink(server_conf['pidfile'])


def create_pid():
    atexit.register(remove_pid)
    with open(server_conf['pidfile'], "w") as f:
        f.write(str(os.getpid()))


def start_server():
    logger.info("starting server")
    app.run(host=server_conf['host'], port=int(server_conf['port']), debug=str2bool(server_conf['debug']))


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')

    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')

    func()


def init():
    load_config()
    configure_logging()
    create_pid()
    setup_db()
    load_data()


if __name__ == '__main__':
    init()
    start_server()
