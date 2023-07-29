from flask import Flask, make_response, request, url_for, send_from_directory
import sqlite3
import gradio as gr
import os
from PIL import Image
import io

app = Flask(__name__)

def getdb ():
    conn = sqlite3.connect('images-tags.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/<path:path>')
def send_report(path):
    return send_from_directory('web/dist', path)

@app.route("/api/image/<int:id>")
def image(id: int):
    with getdb() as conn:
        c = conn.cursor()
        c.execute('SELECT id, data FROM images where id = ?', (id,))
        data = c.fetchone()['data']
        c.close()

    res = make_response(data)
    res.headers['Content-Type'] = 'image/jpeg'

    return res

@app.route("/api/random")
def random ():
    limit = request.args.get('limit', 20, int)
    with getdb() as conn:
        c = conn.cursor()
        c.execute('select id, tags from posts order by random() limit ?', (limit, ))
        rows = c.fetchall()

        results = []
        for row in rows:
            results.append({
                "id": row['id'],
                "tags": row['tags']
            })

        return results

app.run()