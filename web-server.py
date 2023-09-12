from flask import Flask, make_response, request, url_for, send_from_directory
import sqlite3
import gradio as gr
import random as rrr
from PIL import Image
import io

app = Flask(__name__)

def excludeTags (str):
    f = open('exclude.txt', 'r')
    for line in f.readlines():
        str = str.replace(line.strip(), '')
    f.close()
    return str

def replaceTags (str):
    f = open('replace.txt', 'r')
    for line in f.readlines():
        pair = line.split()
        str = str.replace(pair[0], pair[1])
    f.close()
    return str

def getdb (dbname = 'images-tags.db'):
    conn = sqlite3.connect(dbname)
    conn.row_factory = sqlite3.Row
    return conn

def get_tags_filterCount (tags = ''):
    tag_list = [n for n in tags.split(' ') if n.strip() != '']
    tag_list = ["'" + item + "'" if isinstance(item, str) else item for item in tag_list]
    
    if len(tag_list) == 0:
        tagsFilter = ''
    elif len(tag_list) == 1:
        tagsFilter = f'where tags.tag like "%{tags}%"'
    elif len(tag_list) > 1:
        tagsFilter = f'where tags.tag in ({", ".join(tag_list)})'
    
    return tagsFilter, len(tag_list)

@app.route('/<path:path>')
def send_report(path):
    return send_from_directory('web/dist', path)

@app.route("/api/image/<int:id>")
def image(id: int):
    with getdb('images-data.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, data FROM images where id = ?', (id,))
        data = c.fetchone()['data']
        c.close()

    res = make_response(data)
    res.headers['Content-Type'] = 'image/jpeg'

    return res

@app.route("/api/random/1")
def random_1 ():
    tags = request.args.get('tags', '', str)
    dbName = request.args.get('db', 'images-tags.db', str)
    with getdb(dbName) as conn:
        (tagsFilter, tagCount) = get_tags_filterCount(tags)
        c = conn.cursor()
        c.execute('SELECT count(1) as c FROM posts')
        row = c.fetchone()
        count = row['c']
        offset = rrr.randrange(0, count)

        sqlstr = f'''select post_id id, tags, file_url from tags
inner join posts on posts.id = post_id
{tagsFilter}
GROUP by post_id
having count(tags.tag) >= {tagCount}
limit 1 offset {offset}'''
        c.execute(sqlstr)
        rows = c.fetchall()
        c.close()

        results = []
        for row in rows:
            tags = replaceTags(excludeTags(row['tags']))
            results.append({
                "id": row['id'],
                "tags": tags,
                "file_url": row["file_url"]
            })

        return results

@app.route("/api/random")
def random ():
    limit = request.args.get('limit', 20, int)
    tags = request.args.get('tags', '', str)
    dbName = request.args.get('db', 'images-tags.db', str)
    with getdb(dbName) as conn:
        (tagsFilter, tagCount) = get_tags_filterCount(tags)

        sqlstr = f'''select post_id id, tags from tags
inner join posts on posts.id = post_id
{tagsFilter}
GROUP by post_id
having count(tags.tag) >= {tagCount}
order by random()
limit ?'''
        c = conn.cursor()
        c.execute(sqlstr, (limit, ))
        rows = c.fetchall()
        c.close()

        results = []
        for row in rows:
            tags = replaceTags(excludeTags(row['tags']))
            results.append({
                "id": row['id'],
                "tags": tags
            })

        return results

app.run()