from flask import Flask, make_response, request, url_for, send_from_directory, abort, jsonify
from flask_cors import CORS, cross_origin
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
import random
import app_cpu
import requests
import logging
import time
from logging.handlers import RotatingFileHandler

# 配置日志记录器
handler = RotatingFileHandler('access.log', maxBytes=10000000, backupCount=5)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s'
))
handler.setLevel(logging.INFO)

app = Flask(__name__)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# 添加请求日志记录中间件
@app.before_request
def log_request_info():
    # 只记录 POST 请求
    if request.method == 'POST':
        # 获取请求体内容
        body = request.get_data(as_text=True)
        # 记录请求信息和请求体
        app.logger.info('Request: %s %s %s\nBody: %s', request.method, request.url, request.remote_addr, body)

@app.after_request
def log_response_info(response):
    # 只记录 POST 请求
    if request.method == 'POST':
        app.logger.info('Response: %s %s %s %s', request.method, request.url, response.status_code, response.content_length)
    return response

CORS(app)

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

        if tag_zh == '':
            return []

        if (tag_zh.isascii()):
            c.execute(f'select id from tags_{rating} where tag like %s', (tag_zh,))
            rows = c.fetchall()
            result = [ item['id'] for item in rows ]
        else:
            c.execute(f'select id from tags_{rating} where tag_zh like %s', (tag_zh,))
            rows = c.fetchall()
            result = [ item['id'] for item in rows ]

        return result
    
def get_tagid_by_zh2 (tag_zh: str, rating: str, pg_conn):
    with pg_conn.cursor() as c:
        result = []
        tag_zh = tag_zh.replace('\\', '\\\\')

        if tag_zh == '':
            return []

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
    with getdb_pg().cursor() as c:
        c.execute(f'SELECT * FROM tags_s where tag like %s or tag_zh like %s limit 10', (tag_p, tag_p))
        rows = c.fetchall()
        result = []
        for row in rows:
            result.append({
                'tag': row['tag'].replace('\\(', '(').replace('\\)', ')'),
                'tag_zh': row['tag_zh']
            })
        return result


@app.route("/api/image/<int:id>")
@app.route("/api/image/<int:id>.jpg")
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
    

    res.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return res

@app.route("/api/image/<int:id>/wd14")
def image_wd14 (id: int):
    with getdb('images-data.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, data FROM images where id = ?', (id,))
        data = c.fetchone()['data']
        c.close()
    
    image = Image.open(io.BytesIO(data))
    tags = app_cpu.image_to_wd14_tags(image, 'wd-eva02-large-tagger-v3', 0.35, True, True, False, True)

    return tags

@app.route("/api/image2/<int:id>")
def image2(id: int):
    with psycopg2.connect("dbname=postgres user=real", cursor_factory=RealDictCursor) as pg_conn, pg_conn.cursor() as c:
        c.execute('SELECT id, data FROM image_data where id = %s', (id,))
        data = c.fetchone()['data']
        data = data.tobytes()

    blur_value = request.args.get('blur', None, str)
    reverse_value = request.args.get('reverse', None, str)

    if (not blur_value) and (not reverse_value):
        res = make_response(data)
        res.headers['Content-Type'] = 'image/webp'
    else:
        if blur_value:
            image = Image.open(io.BytesIO(data))
            blur = ImageFilter.GaussianBlur(radius=int(blur_value))
            image = image.filter(blur)
            image_io = io.BytesIO()
            image.save(image_io, 'WEBP')  # You can choose the format you want (PNG, JPEG, etc.)
            image_io.seek(0)
            res = make_response(image_io)
            res.headers['Content-Type'] = 'image/webp'
        if reverse_value:
            image = Image.open(io.BytesIO(data))
            image = reverse_phase(image)
            image_io = io.BytesIO()
            image.save(image_io, 'WEBP')
            image_io.seek(0)
            res = make_response(image_io)
            res.headers['Content-Type'] = 'image/webp'
    

    res.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return res

@app.route("/api/random/tags")
def random_tags ():
    limit = request.args.get('limit', 20)
    factor = request.args.get('factor', 1)

    with getdb_pg().cursor() as c:
        c.execute(f'select tag from tags_s order by probability + (random() * %s) desc limit %s', (factor, limit))
        rows = c.fetchall()
        result = []

        for row in rows:
            result.append(row['tag'])
        
        return ', '.join(result)


@app.route("/api/random/3", methods=['POST'])
@cross_origin()
def random_3 ():
    json_text = request.get_data(as_text=True)
    json_data = json.loads(json_text)

    rating = json_data['rating']
    and_array = json_data['and_array']
    or_array = json_data['or_array']
    not_array = []
    if 'not_array' in json_data:
        not_array = json_data['not_array']

    until_id = json_data['until_id'] if 'until_id' in json_data else None
    limit = json_data['limit'] if 'limit' in json_data else 1

    and_array = remvoe_duplicate(and_array)
    
    with getdb_pg().cursor() as c:
        try:
            and_tag_list = []
            or_tag_list = []
            not_tag_list = []

            for and_tag in and_array:
                and_tag_list = and_tag_list + get_tagid_by_zh(and_tag, rating)

            for or_tag in or_array:
                or_tag_list_item = []
                for or_tag_item in or_tag:
                    or_tag_list_item = or_tag_list_item + (get_tagid_by_zh(or_tag_item, rating))
                or_tag_list.append(or_tag_list_item)

            for not_tag in not_array:
                not_tag_list_item = []
                for not_tag_item in not_tag:
                    not_tag_list_item = not_tag_list_item + (get_tagid_by_zh(not_tag_item, rating))
                not_tag_list.append(not_tag_list_item)

            sqlstr = f'select p.id from posts_{rating} p\n'
            
            if 'tablesample' in json_data and json_data['action'] == 'search':
                tablesample = json_data['tablesample']
                # sqlstr += f'TABLESAMPLE BERNOULLI ({tablesample})\n'

            t_index = 1

            for and_tag_id in and_tag_list:
                sqlstr += f'inner join post_tag_{rating} pt{t_index} on pt{t_index}.post_id = p.id and pt{t_index}.tag_id = {and_tag_id}\n'
                t_index += 1
            
            for or_tag_ids in or_tag_list:
                ids_str = ', '.join(map(str, or_tag_ids))
                sqlstr += f'inner join post_tag_{rating} pt{t_index} on pt{t_index}.post_id = p.id and pt{t_index}.tag_id in ({ids_str})\n'
                t_index += 1
            
            for not_tag_ids in not_tag_list:
                ids_str = ', '.join(map(str, not_tag_ids))
                # sqlstr += f'inner join post_tag_{rating} pt{t_index} on pt{t_index}.post_id = p.id and pt{t_index}.tag_id not in ({ids_str})\n'
                
                t_index += 1

            # sqlstr += 'group by p.id,p.score,p.tags,p.file_url,p.source,p.tags_yande\n'
            
            # c.execute(f'select max(id) max_id, min(id) min_id from posts_{rating}')
            # rows = c.fetchall()
            # max_id = rows[0]['max_id']
            # min_id = rows[0]['min_id']
            # target_id = random.randint(min_id, max_id)
            # sqlstr += f'where p.id > {target_id} '

            sqlstr += f'where 1=1\n'
            
            if 'score' in json_data:
                score = json_data['score']
                sqlstr += f' and score >= {score}\n'

            if until_id and until_id > 0:
                sqlstr += f' and p.id < {until_id}\n'

            if 'action' in json_data:
                action = json_data['action']
                page_begin_id = json_data['page_begin_id']
                page_end_id = json_data['page_end_id']

                if action == 'newest':
                    sqlstr += f'order by id desc\n'
                elif action == 'oldest':
                    sqlstr += f'order by id asc\n'
                elif action == 'next':
                    sqlstr += f'and id > {page_end_id}\n'
                    sqlstr += f'order by id asc\n'
                elif action == 'prev':
                    sqlstr += f'and id < {page_begin_id}\n'
                    sqlstr += f'order by id desc\n'
                elif action == 'search':
                    sqlstr += f'order by id desc\n'
            else:
                sqlstr += f'order by random() asc\n'

            sqlstr += f'limit {limit}\n'

            sqlstr_select = (f'select distinct p.id,p.score,p.tags,p.file_url,p.source,p.tags_yande,p.sample_width, p.sample_height from posts_{rating} p\n'
            + f'where exists (select 1 from ({sqlstr}) sub where sub.id = p.id)\n')

            print(sqlstr_select)
            c.execute(sqlstr_select)
            rows = c.fetchall()
            
            result = []
            post_id_list = []
            for row in rows:
                post_id_list.append(str(row['id']))
                result.append({
                    "id": row['id'],
                    "tags": row['tags'],
                    "tags_zh": "",
                    "file_url": row["file_url"],
                    "score": row['score'],
                    "source": row['source'],
                    "tags_yande": row['tags_yande'],
                    "width": row['sample_width'],
                    "height": row['sample_height']
                })

            # post_id_list_join = ', '.join(post_id_list)
            # c.execute(f'UPDATE posts_{rating} set ro = random() * 2147483647 where id in ({post_id_list_join})')
            # c.execute(f'select sum(ro) / count(ro) as ro_avg from posts_{rating}')
            # ro_avg = c.fetchone()['ro_avg']
#             c.execute(f'''
# update posts_s set ro = ({ro_avg}) - (random() * {limit}) 
# where id in (
# select id from posts_s 
# order by ro asc
# limit {limit}
# )
# ''')
            pg_conn.commit()

            return result
        except Exception as err:
            getdb_pg().rollback()
            raise err
        
@app.route("/api/random/4", methods=['POST'])
def random_4 ():
    json_text = request.get_data(as_text=True)
    json_data = json.loads(json_text)

    rating = json_data['rating']
    and_array = json_data['and_array']
    or_array = json_data['or_array']
    limit = json_data['limit'] if 'limit' in json_data else 1

    and_array = remvoe_duplicate(and_array)
    
    with psycopg2.connect("dbname=postgres user=real", cursor_factory=RealDictCursor) as pg_conn, pg_conn.cursor() as c:
        try:
            and_tag_list = []
            or_tag_list = []

            for and_tag in and_array:
                and_tag_list = and_tag_list + get_tagid_by_zh2(and_tag, 'real', pg_conn)

            for or_tag in or_array:
                or_tag_list_item = []
                for or_tag_item in or_tag:
                    or_tag_list_item = or_tag_list_item + (get_tagid_by_zh2(or_tag_item, 'real', pg_conn))
                or_tag_list.append(or_tag_list_item)

            sqlstr = f'select p.id,p.tags from posts_real p\n'
            t_index = 1

            for and_tag_id in and_tag_list:
                sqlstr += f'inner join post_tag_real pt{t_index} on pt{t_index}.post_id = p.id and pt{t_index}.tag_id = {and_tag_id}\n'
                t_index += 1
            
            for or_tag_ids in or_tag_list:
                ids_str = ', '.join(map(str, or_tag_ids))
                sqlstr += f'inner join post_tag_real pt{t_index} on pt{t_index}.post_id = p.id and pt{t_index}.tag_id in ({ids_str})\n'
                t_index += 1

            # sqlstr += 'group by p.id,p.score,p.tags,p.file_url,p.source,p.tags_yande\n'
            sqlstr += f'where rating = %s\n'
            sqlstr += f'order by random()\n'
            sqlstr += 'limit %s\n'

            print(sqlstr)
            c.execute(sqlstr, (rating, limit))
            rows = c.fetchall()
            
            result = []
            post_id_list = []
            for row in rows:
                post_id_list.append(str(row['id']))
                result.append({
                    "id": row['id'],
                    "tags": row['tags'],
                    "tags_zh": "",
                    "link": "/api/image2/" + str(row['id'])
                })

            return result
        except Exception as err:
            getdb_pg().rollback()
            raise err
        
@app.route("/api/random/5", methods=['POST'])
def random_5 ():
    json_text = request.get_data(as_text=True)
    json_data = json.loads(json_text)

    score = json_data['score']
    rating = json_data['rating']
    limit = json_data['limit'] if 'limit' in json_data else 1

    with getdb_pg().cursor() as c:
        sql_where = f'where 1=1'
        if score > 0:
            sql_where += f' and score >= {score}'
        sqlstr = f'select * from posts_{rating} {sql_where} order by random() limit %s'
        c.execute(sqlstr, (limit,))
        rows = c.fetchall()


        result = []
        for row in rows:
            result.append({
                "id": row['id'],
                "file_url": row['file_url'],
                "width": row['sample_width'],
                "height": row['sample_height'],
                "file_ext": row['file_ext']
            })

        return result


@app.route("/api/remove_score", methods=['GET'])
def remove_score ():
    limit = request.args.get('limit', 100)
    ids = []
    
    with getdb_pg().cursor() as c:
        c.execute(f'select id from posts_s where score < 20 order by updated_at asc limit %s', (limit,))
        rows = c.fetchall()
        ids = [row['id'] for row in rows]
        c.execute(f"delete from posts_s where id in ({','.join(['%s'] * len(ids))})", ids)
        c.execute(f"delete from post_tag_s where post_id in ({','.join(['%s'] * len(ids))})", ids)
        getdb_pg().commit()
        
    with getdb('images-data.db') as conn:
        c = conn.cursor()
        c.execute(f"delete from images where id in ({','.join(['?'] * len(ids))})", ids)
        conn.commit()
        c.close()
        return ids
    

@app.route("/api/gelbooru/posts")
def gelbooru_proxy():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'}
    # 从请求中获取所有查询参数
    params = request.args.to_dict()
    
    # 构建 Gelbooru API URL
    gelbooru_url = "https://gelbooru.com/index.php"
    
    try:
        # 使用 requests 转发请求到 Gelbooru
        response = requests.get(gelbooru_url, params=params, headers=headers)
        
        # 返回 Gelbooru 的响应
        return response.json()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/save-pagemap", methods=['POST'])
def save_pagemap():
    data = request.get_data(as_text=True)
    
    # 将数据保存到本地文件
    try:
        with open('pagemap.json', 'w', encoding='utf-8') as f:
            f.write(data)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/load-pagemap", methods=['GET'])
def load_pagemap():
    try:
        # 尝试从本地文件读取数据
        with open('pagemap.json', 'r', encoding='utf-8') as f:
            data = f.read()
        return data, 200, {'Content-Type': 'application/json'}
    except FileNotFoundError:
        # 如果文件不存在，返回空对象
        return jsonify({}), 200
    except Exception as e:
        # 处理其他可能的错误
        return jsonify({"status": "error", "message": str(e)}), 500

app.run()