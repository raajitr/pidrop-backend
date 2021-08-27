import datetime
import io
import base64
import urllib.parse
from flask import Flask, render_template, request, send_file, jsonify
from tinydb import TinyDB, Query
from tinydb_smartcache import SmartCacheTable

app = Flask(__name__)

db = TinyDB('db.json')
TinyDB.table_class = SmartCacheTable

text_types = ['txt', 'rtf', 'html']
media_type = ['pdf', 'png', 'jpg', 'jpeg', 'mp4', 'gif']
image_type = ['png', 'jpg', 'jpeg', 'gif']


@app.route("/")
def home_page():
    clipboard = [
        {
            "timestamp": datetime.datetime.fromisoformat(c['timestamp']).strftime("%a, %-d/%-m, %H:%M:%S"),
            "content": construct_content(c['data'], c['type'], c['timestamp']),
            "type": c['type'], 
            "is_text": c['type'] in ['txt', 'rtf']
        } for c in sorted(db.all(), key=lambda x: x['timestamp'], reverse=True)
    ]

    return render_template("index.html",
                           clipboard=clipboard)

@app.route("/rest")
def get_all():
    clipboard = [
        {
            "timestamp": c['timestamp'],
            "content": construct_content(c['data'], c['type'], c['timestamp']),
            "type": c['type'], 
            "ctype": c.get('ctype') or 'other',
            "isImage": c['type'] in image_type,
            "customMedia": c['type'] not in text_types
        } for c in sorted(db.all(), key=lambda x: x['timestamp'], reverse=True)
    ]

    response = jsonify(clipboard)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route("/record", methods=["POST"])
def paste():
    data = request.form['data'] or None
    _type = request.form['type'] or None
    
    if data and _type: 
        pass
    else: 
        return "Nothing sent", 500

    timestamp = datetime.datetime.now().isoformat()
    db.insert({
        'timestamp': timestamp,
        'data': data,
        'type': _type,
        'ctype': 'text' if _type in text_types[:-1] else 'link'
    })

    response = jsonify({"response": "SUCCESS"})
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response

@app.route('/media/<timestamp>')
def send_media(timestamp):
    timestamp = urllib.parse.unquote(timestamp)
    timestamp = timestamp.replace('s', '.')
    record = db.get(Query()['timestamp'] == timestamp)

    as_download = bool(request.args.get('download'))

    mimetype_map, all_mimetype = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'mp4': 'video/mp4',
        'pdf': 'application/pdf',
        'heic': 'image/heic'
    }, 'application/octet-stream'

    mimetype = mimetype_map.get(record['type'], all_mimetype)

    readable_time = datetime.datetime.fromisoformat(timestamp).strftime("%H%M on %a")

    # little bit of cleanup
    data_to_send = record['data']
    # add extra padding.
    data_to_send += '=='
    # remove prepended data info, if any
    data_to_send = data_to_send.split(',')[-1]

    return send_file(
        io.BytesIO(base64.b64decode(data_to_send)),
        mimetype=mimetype,
        as_attachment=as_download,
        attachment_filename="Clipboard Media at {}".format(readable_time),
    )    

def construct_content(data, _type, timestamp):
    if _type in text_types:
        return str(base64.b64decode(data), 'utf-8')
    timestamp = timestamp.replace('.', 's')
    return '{}media/{}'.format(request.host_url, urllib.parse.quote_plus(timestamp))


if __name__=='__main__':
    app.run(host='0.0.0.0', debug=True)
