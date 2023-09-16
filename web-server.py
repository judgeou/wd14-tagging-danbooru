from flask import Flask, make_response, request, url_for, send_from_directory, abort
import sqlite3
import gradio as gr
import random as rrr
from PIL import Image, ImageFilter
import io
import numpy as np

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

def add_single_quotes_to_csv_elements(input_string):
    elements = input_string.split(',')
    result_string = ','.join(f"'{element}'" for element in elements)
    return result_string

def get_tags_zh_filter (tags_zh = ''):
    tags_zh_list = tags_zh.split(' ')
    tags_zh_list_chs = [item for item in tags_zh_list if not item.isascii()]
    tags_zh_list_ascii = [item for item in tags_zh_list if item.isascii()]

    with getdb('danbooru-tag-zh.db') as conn:
        c = conn.cursor()
        c.execute(f'''select group_concat(tag, ',') tag_group, tag_zh, count(1) c from tags where tag_zh in ({", ".join(["?" for _ in tags_zh_list_chs])}) group by tag_zh''', tuple(tags_zh_list_chs))
        rows = c.fetchall()

        if rows is None:
            return (None,0)

        condition_list = []
        for row in rows:
            condition_list.append(add_single_quotes_to_csv_elements(row['tag_group']))

        for row in tags_zh_list_ascii:
            r = row.replace('(', '\\(').replace(')', '\\)')
            condition_list.append(f"'{r}'")
        
        return (' tags.tag in (' + ','.join(condition_list) + ')', len(rows) + len(tags_zh_list_ascii))
    
def reverse_phase(image: Image.Image):
    # Convert the input image to a NumPy array
    image_array = np.array(image)

    # Reverse the phase by subtracting the array from the maximum (255 for uint8)
    reversed_array = 255 - image_array

    # Create a new PIL image from the reversed NumPy array
    reversed_image = Image.fromarray(reversed_array)

    return reversed_image

@app.route('/<path:path>')
def send_report(path):
    return send_from_directory('web/dist', path)

@app.route("/api/search/tag")
def search_tag ():
    tag = request.args.get('tag', '', str)
    tag_p = f'%{tag}%'
    with getdb('images-tags.db') as conn:
        c = conn.cursor()
        
        if tag.isascii():
            c.execute(f'''
SELECT tag from tags
where tag like ?
GROUP by tag
limit 20
''', (tag_p, ))
        else:
            c.execute(f'''
SELECT dan_zh.tag_zh tag from dan_zh
INNER join tags ttt on ttt.tag = dan_zh.tag
where dan_zh.tag_zh like ?
GROUP by dan_zh.tag_zh
limit 20
''', (tag_p,))
            
        rows = c.fetchall()
        c.close()

        result = []
        for row in rows:
            result.append({
                'tag': row['tag'].replace('\\(', '(').replace('\\)', ')')
            })
        return result

@app.route("/api/add-tag-zh", methods=['POST'])
def add_tag_zh ():
    data = request.get_json()

@app.route("/api/image/<int:id>")
def image(id: int):
    with getdb('images-data.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, data FROM images where id = ?', (id,))
        data = c.fetchone()['data']
        c.close()

    blur_value = request.args.get('blur', None, str)
    reverse_value = request.args.get('reverse', None, str)

    if (not blur_value) and (not reverse_value):
        res = make_response(data)
        res.headers['Content-Type'] = 'image/jpeg'
    else:
        if blur_value:
            image = Image.open(io.BytesIO(data))
            blur = ImageFilter.GaussianBlur(radius=int(blur_value))
            image = image.filter(blur)
            image_io = io.BytesIO()
            image.save(image_io, 'JPEG')  # You can choose the format you want (PNG, JPEG, etc.)
            image_io.seek(0)
            res = make_response(image_io)
            res.headers['Content-Type'] = 'image/jpeg'
        if reverse_value:
            image = Image.open(io.BytesIO(data))
            image = reverse_phase(image)
            image_io = io.BytesIO()
            image.save(image_io, 'JPEG')
            image_io.seek(0)
            res = make_response(image_io)
            res.headers['Content-Type'] = 'image/jpeg'
    


    return res

@app.route("/api/random/score")
def random_score ():
    score = request.args.get('score', 100, int)
    dbName = request.args.get('db', 'images-tags.db', str)

    with getdb(dbName) as conn:
        c = conn.cursor()
        c.execute('select id, tags, file_url from posts where score >= ? order by random() limit 1', (score,))
        row = c.fetchone()
        if (row is None):
            abort(404)
        else:
            return {
                'id': row['id'],
                'file_url': row['file_url']
            }


@app.route("/api/random/2")
def random_2 ():
    tags_param = request.args.get('tags', '女孩', str)
    tags_param = tags_param if tags_param else '女孩'

    dbName = request.args.get('db', 'images-tags.db', str)

    with getdb('danbooru-tag-zh.db') as conn_tag_zh:
    
        with getdb(dbName) as conn:
            (tagsFilter, haveCount) = get_tags_zh_filter(tags_param)
            
            c = conn.cursor()
            sqlstr = f'select post_id from tags where {tagsFilter} group by post_id having count(1) >= {haveCount} order by random() limit ? '
            print(sqlstr)
            c.execute(sqlstr, (1,))
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
            c.execute(f'''select group_concat(tag_zh, ' ') tags_zh, group_concat(tag, ',') tags_en from tags where tag in ({", ".join(["?" for _ in tags_list])})''', tuple(tags_list))
            row = c.fetchone()
            tags_zh = row['tags_zh']
            tags_en = row['tags_en']
            tags_en_list = tags_en.split(',')
            tags_not_in_zh = set(tags_list) - set(tags_en_list)
            row = c.fetchone()
            c.close()

            return {
                "id": id,
                "tags": tags,
                "tags_zh": (tags_zh + ' ' + ' '.join(tags_not_in_zh)).replace('\\(', '(').replace('\\)', ')'),
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