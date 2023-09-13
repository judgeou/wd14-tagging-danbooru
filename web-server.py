from flask import Flask, make_response, request, url_for, send_from_directory, abort
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

    paramValue = tuple()
    
    if len(tag_list) == 0:
        tagsFilter = ''
    elif len(tag_list) == 1:
        tagsFilter = f'where tags.tag like ?'
        paramValue = (f'%{tags.strip()}%', )
    elif len(tag_list) > 1:
        tagsFilter = f'where tags.tag in ({", ".join(["?" for _ in tag_list])})'
        paramValue = tuple(tag_list)
    
    return tagsFilter, paramValue

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

@app.route("/api/random/2")
def random_2 ():
    tags_param = request.args.get('tags', '女孩', str)
    tags_param = tags_param if tags_param else '女孩'

    dbName = request.args.get('db', 'images-tags.db', str)
    tags_zh_list = tags_param.split(' ')
    tags_zh_list = [item for item in tags_zh_list if item]

    tag_list = ''

    with getdb('danbooru-tag-zh.db') as conn_tag_zh:
        c = conn_tag_zh.cursor()
        c.execute(f'''select group_concat(tag, ' ') as tag_list from "tags" where tag_zh in ({", ".join(["?" for _ in tags_zh_list])})''', tuple(tags_zh_list))
        row = c.fetchone()
        tag_list = row['tag_list']
        c.close()
        if (tag_list is None):
            abort(404)
    
        with getdb(dbName) as conn:
            (tagsFilter, paramValue) = get_tags_filterCount(tag_list)
            
            c = conn.cursor()
            executeParams = paramValue + (1, )
            havingCondition = f'HAVING count(1) = {len(paramValue)}' if len(paramValue) > 0 else ''
            c.execute(f'select post_id from tags {tagsFilter} GROUP BY post_id {havingCondition} order by random() limit ? ', executeParams)
            row = c.fetchone()

            if not row:
                abort(404)

            id = row['post_id']

            c.execute('select id, tags, file_url from posts where id = ?', (id, ))
            row = c.fetchone()
            c.close()
            tags = row['tags']
            file_url = row["file_url"]
            
            tags_list = tags.split(',')
            tags_list = [s.strip() for s in tags_list]

            c = conn_tag_zh.cursor()
            c.execute(f'''select group_concat(tag_zh, ' ') tags_zh from tags where tag in ({", ".join(["?" for _ in tags_list])})''', tuple(tags_list))
            row = c.fetchone()
            tags_zh = row['tags_zh']
            c.close()

            return {
                "id": id,
                "tags": tags,
                "tags_zh": tags_zh,
                "file_url": file_url
            }

@app.route("/api/random/1")
def random_1 ():
    limit = request.args.get('limit', 20, int)
    tags = request.args.get('tags', '', str)
    dbName = request.args.get('db', 'images-tags.db', str)
    with getdb(dbName) as conn:
        (tagsFilter, paramValue) = get_tags_filterCount(tags)
        c = conn.cursor()

        post_id_list = []

        executeParams = paramValue + (limit, )
        havingCondition = f'HAVING count(1) = {len(paramValue)}' if len(paramValue) > 0 else ''
        c.execute(f'select post_id from tags {tagsFilter} GROUP BY post_id {havingCondition} order by random() limit ? ', executeParams)
        rows = c.fetchall()

        for row in rows:
            post_id_list.append(row['post_id'])

        sqlstr = f'select id, tags, file_url from posts where id in ({", ".join(map(str, post_id_list))})'
        c.execute(sqlstr)
        rows = c.fetchall()

        results = []
        for row in rows:
            tags = replaceTags(excludeTags(row['tags']))
            results.append({
                "id": row['id'],
                "tags": tags,
                "file_url": row["file_url"]
            })
        
        c.close()

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