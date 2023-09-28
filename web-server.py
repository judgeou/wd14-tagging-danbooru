from flask import Flask, make_response, request, url_for, send_from_directory, abort
import sqlite3
import gradio as gr
import random as rrr
from PIL import Image, ImageFilter
import io
import numpy as np
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import urllib.request
from io import BytesIO

app = Flask(__name__)

pg_conn = psycopg2.connect("dbname=postgres user=dan", cursor_factory=RealDictCursor)

def downloadFile (url: str):
    while True:
      try:
        req = urllib.request.Request(
            url, 
            data=None, 
            headers={
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.1916.47 Safari/537.36'
            }
        )

        res = urllib.request.urlopen(req)
        sample_data = res.read()
        break
      except Exception as e:
        print(e)
        continue
    
    image_stream = BytesIO(sample_data)
    return image_stream

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

def remvoe_duplicate (arr: list):
    unique_list = []

    for item in arr:
        if item not in unique_list:
            unique_list.append(item)

    return unique_list

def getdb (dbname = 'images-tags.db'):
    conn = sqlite3.connect(dbname)
    conn.row_factory = sqlite3.Row
    return conn

def getdb_pg ():
    global pg_conn
    if (pg_conn is None or pg_conn.closed):
        pg_conn = psycopg2.connect("dbname=postgres user=dan", cursor_factory=RealDictCursor)
    return pg_conn

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

def get_question_mark_str (arr = []):
    return ", ".join(["?" for _ in arr])

def strip_list (str_list = []):
    stripped_list = [s.strip() for s in str_list]
    return stripped_list

def remove_blank (str_list = []):
    result = [s for s in str_list if s.strip()]
    return result

def get_tag_by_zh (tag_zh = ''):
    if (tag_zh.isascii()):
        return [ tag_zh ]
    
    with getdb('danbooru-tag-zh.db') as conn:
        c = conn.cursor()
        c.execute(f'SELECT tag FROM tags where tag_zh = ?', (tag_zh, ))
        rows = c.fetchall()
        c.close()
        result = []
        for row in rows:
            result.append(row['tag'])
        return result

def get_tagid_by_zh (tag_zh: str, rating: str):
    with getdb_pg().cursor() as c:
        result = []
        tag_zh = tag_zh.replace('\\', '\\\\')

        if (tag_zh.isascii()):
            c.execute(f'select id from tags_{rating} where tag like %s', (tag_zh,))
            rows = c.fetchall()
            result = [ item['id'] for item in rows ]
        else:
            c.execute(f'select id from tags_{rating} where tag_zh like %s', (tag_zh,))
            rows = c.fetchall()
            result = [ item['id'] for item in rows ]

        return result

def get_tag_group_str (tags = ''):
    tags_zh_list_chs = [item for item in tags if not item.isascii()]

    with getdb('danbooru-tag-zh.db') as conn:
        c = conn.cursor()
        c.execute(f'''select group_concat(tag, ',') tag_group, tag_zh, count(1) c from tags where tag_zh in ({", ".join(["?" for _ in tags_zh_list_chs])}) group by tag_zh''', tuple(tags_zh_list_chs))
        rows = c.fetchall()
        result = []
        for row in rows:
            result.append(row['tag_group'])
        return result

def get_tags_zh_filter (tags_zh = '', tags_zh_or = '', tags_like = ''):
    tags_zh_list = tags_zh.split(' ')
    tags_zh_list_or = [] if len(tags_zh_or) == 0 else remove_blank(tags_zh_or.split(' '))
    tags_list_like = [] if len(tags_like) == 0 else remove_blank(tags_like.split(' '))

    condition_sql_list = []
    param_list = []
    i = 1

    for tags_zh in tags_zh_list:
        tags = get_tag_by_zh(tags_zh)
        condition_sql_list.append(f'JOIN tags t{i} ON t{i}.post_id = tags.post_id AND t{i}.tag in ({get_question_mark_str(tags)})')
        param_list += tags
        i += 1

    for tags_like in tags_list_like:
        condition_sql_list.append(f'JOIN tags t{i} ON t{i}.post_id = tags.post_id AND t{i}.tag like ?')
        param_list.append(tags_like)
        i += 1

    like_list = []

    for tags_zh_or in tags_zh_list_or:
        tags_or = get_tag_by_zh(tags_zh_or)

        for tags_or_item in tags_or:
            like_list.append(f't{i}.tag like ?')
            param_list.append(tags_or_item)
    
    if (len(tags_zh_list_or) > 0):
        like_list_sql = ' or '.join(like_list) 
        condition_sql_list.append(f'JOIN tags t{i} ON t{i}.post_id = tags.post_id AND ({like_list_sql})')
        i += 1

    condition_sql = '\n' + '\n'.join(condition_sql_list)
    return (condition_sql, param_list)
    
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


@app.route("/api/image/<int:id>")
def image(id: int):
    isOriginal = request.args.get('o', None, str)
    with getdb('images-data.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, data FROM images where id = ?', (id,))
        data = c.fetchone()['data']
        c.close()

    if (isOriginal is not None):
        with getdb_pg().cursor() as c:
            c.execute('SELECT * FROM posts_s where id = %s', (id,))
            row = c.fetchone()
            file_url = row['file_url']
            return file_url

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

@app.route("/api/random/3", methods=['POST'])
def random_3 ():
    json_text = request.get_data(as_text=True)
    json_data = json.loads(json_text)

    rating = json_data['rating']
    and_array = json_data['and_array']
    or_array = json_data['or_array']
    limit = json_data['limit'] if 'limit' in json_data else 1

    and_array = remvoe_duplicate(and_array)
    
    with getdb_pg().cursor() as c:
        try:
            and_tag_list = []
            or_tag_list = []

            for and_tag in and_array:
                and_tag_list = and_tag_list + get_tagid_by_zh(and_tag, rating)

            for or_tag in or_array:
                or_tag_list_item = []
                for or_tag_item in or_tag:
                    or_tag_list_item = or_tag_list_item + (get_tagid_by_zh(or_tag_item, rating))
                or_tag_list.append(or_tag_list_item)

            sqlstr = f'select p.id,p.score,p.tags,p.file_url from posts_{rating} p\n'
            t_index = 1

            for and_tag_id in and_tag_list:
                sqlstr += f'inner join post_tag_{rating} pt{t_index} on pt{t_index}.post_id = p.id and pt{t_index}.tag_id = {and_tag_id}\n'
                t_index += 1
            
            for or_tag_ids in or_tag_list:
                ids_str = ', '.join(map(str, or_tag_ids))
                sqlstr += f'inner join post_tag_{rating} pt{t_index} on pt{t_index}.post_id = p.id and pt{t_index}.tag_id in ({ids_str})\n'
                t_index += 1

            sqlstr += 'group by p.id,p.score,p.tags,p.file_url\n'
            sqlstr += 'order by random()\n'
            sqlstr += 'limit %s\n'

            print(sqlstr)
            c.execute(sqlstr, (limit,))
            rows = c.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    "id": row['id'],
                    "tags": row['tags'],
                    "tags_zh": "",
                    "file_url": row["file_url"],
                    "score": row['score']
                })
            
            return result
        except Exception as err:
            getdb_pg().rollback()
            raise err
        
@app.route('/api/random/q')
def random_q ():
    with getdb_pg().cursor() as c:
        c.execute('select * from posts_s where rating = %s order by random() limit 20', ('q',))
        rows = c.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row['id'],
                "tags": row['tags'],
                "tags_zh": "",
                "file_url": row["file_url"],
                "score": row['score']
            })
        return result

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