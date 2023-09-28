import sqlite3
import json
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import time
import threading
from io import BytesIO
from PIL import Image
import requests
import app
import psycopg2
from psycopg2.extras import RealDictCursor

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'}

def getdb (dbname = 'images-tags.db'):
    conn = sqlite3.connect(dbname)
    conn.row_factory = sqlite3.Row
    return conn

lock = threading.Lock()

def get_post (id, rating: str, c):
    c.execute(f'SELECT * FROM posts_{rating} where id = %s', (id,))
    row = c.fetchone()
    return row

def has_nsfw_tag (tag_arr: list[str]):
   nsfw_tag_list = ['nipples', 'pussy', 'monochrome', 'female_pubic_hair']
   for tag in tag_arr:
      tag_s = tag.strip()
      for nsfw_tag in nsfw_tag_list:
         if tag_s == nsfw_tag:
            return True
         
   return False

def ensure_image_data (post):
  id = post['id']
  sample_url = post['sample_url']

  with getdb('images-data.db') as conn_data:
    c2 = conn_data.cursor()
    c2.execute('SELECT id, data FROM images where id = ?', (id,))
    row = c2.fetchone()
    
    if (row is not None):
       image_data = row['data']
    else:
      while True:
        try:
          req = urllib.request.Request(
              sample_url, 
              data=None, 
              headers={
                  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.1916.47 Safari/537.36'
              }
          )

          res = urllib.request.urlopen(req)
          image_data = res.read()

          c2.execute('INSERT INTO images (id, data) values (?, ?)', (id, image_data))
          break
        except Exception as e:
          print(e)
          continue

    c2.close()
    conn_data.commit()
    return image_data

def add_post (post, pg_conn):
  try:
    if ('sample_url' not in post):
       return post['id']
  
    id = post['id']
    file_ext = post['file_ext']
    sample_url = post['sample_url']
    file_url = post['file_url']
    sample_width = post['sample_width']
    sample_height = post['sample_height']
    score = post['score']
    updated_at = post['updated_at']
    rating = post['rating']
    tags_yande = post['tags']
    source = post['source']

    image_data = ensure_image_data(post)
    image_stream = BytesIO(image_data)
    image = Image.open(image_stream)

    tags = app.image_to_wd14_tags(image, 'wd14-convnext', 0.35, False, True, False, True)
    tag_list = tags.split(',')
    tag_list += tags_yande.split(' ')
    isNSFW = has_nsfw_tag(tag_list)
    
    rating_flag = ''
    if rating == 's':
       rating_flag = 's'
    elif rating == 'e':
       rating_flag = 'e'
    elif rating == 'q':
       rating_flag = 'e' if isNSFW else 's'

    c = pg_conn.cursor()

    post = get_post(id, rating_flag, c)

    if (post is None):
      c.execute(f'INSERT INTO posts_{rating_flag} (id, file_ext, sample_url, file_url, sample_width, sample_height, score, updated_at, tags, rating, tags_yande, source) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', 
        (id, file_ext, sample_url, file_url, sample_width, sample_height, score, updated_at, tags, rating, tags_yande, source))
    else:
      c.execute(f'UPDATE posts_{rating_flag} set file_ext = %s, sample_url = %s, file_url = %s, sample_width = %s, sample_height = %s, score = %s, updated_at = %s, tags = %s, rating = %s, tags_yande = %s, source = %s WHERE id = %s', 
        (file_ext, sample_url, file_url, sample_width, sample_height, score, updated_at, tags, rating, tags_yande, source, id))

    c.execute(f'DELETE FROM post_tag_{rating_flag} where post_id = %s', (id,))

    for tag in tag_list:
      with lock:
        t = tag.strip()
        c.execute(f'SELECT id from tags_{rating_flag} where tag = %s', (t,))
        row = c.fetchone()
        
        if row is None:
            c.execute(f'INSERT INTO tags_{rating_flag} (tag) values (%s) RETURNING id;', (t,))
            row = c.fetchone()
        
        c.execute(f'INSERT INTO post_tag_{rating_flag} (post_id, tag_id) values (%s, %s)', (id, row['id']))

    c.close()
    return id
  except Exception as err:
    pg_conn.rollback()
    raise err

def pull_posts (start_id: int, new_old: str) -> list:
  url = 'https://yande.re/post.json'
  id_param = f' id:>{start_id} order:id' if new_old == 'new' else f' id:<{start_id} order:id_desc'
  params = { 'tags': f'{id_param}' }
  while True:
    try:
      response = requests.get(url, params=params,  headers=headers)
      data = response.json()
      break
    except:
       continue

  return data
  

def update_maxminid (max_id: int, min_id: int, c):
  c.execute('update dump_state set max_id = %s, min_id = %s', (max_id, min_id))

def add_post_task (t) -> int:
  (post, pg_conn) = t
  id = post['id']
  rating = post['rating']
  add_post(post, pg_conn)
  print(f'{id}_{rating} done')
  return id

def find_max_iter (iterator) -> int:
    max_value = 0
    
    for number in iterator:
        if number > max_value:
            max_value = number
    
    return max_value

def find_min_iter (iterator) -> int:
    min_value = 2000000000
    
    for number in iterator:
        if number < min_value:
            min_value = number
    
    return min_value

def begin_dump_all ():
  pg_conn = psycopg2.connect("dbname=postgres user=dan", cursor_factory=RealDictCursor)
  
  with pg_conn.cursor() as c:
    c.execute('SELECT * from dump_state')
    dump_state = c.fetchone()
    max_id = dump_state['max_id']
    min_id = dump_state['min_id']
    workers_num = 4

  while True:
    posts = pull_posts(max_id, 'new')

    if len(posts) > 0:
      with ThreadPoolExecutor(max_workers=workers_num) as tpe:
        c = pg_conn.cursor()
        c.execute('BEGIN')
        posts_params = [(post, pg_conn) for post in posts]
        results = tpe.map(add_post_task, posts_params)
        max_id = find_max_iter(results)
        update_maxminid(max_id, min_id, c)
        c.close()
        pg_conn.commit()
        print(f'commit {max_id} done')
    else:
        break
    
  while True:
    posts = pull_posts(min_id, 'old')

    if len(posts) > 0:
      with ThreadPoolExecutor(max_workers=workers_num) as tpe:
        c = pg_conn.cursor()
        c.execute('BEGIN')
        posts_params = [(post, pg_conn) for post in posts]
        results = tpe.map(add_post_task, posts_params)
        min_id = find_min_iter(results)
        update_maxminid(max_id, min_id, c)
        c.close()
        pg_conn.commit()
        print(f'commit {min_id} done')

# begin_dump('rating:s')
# begin_dump_old('q')
# split_image_data()

begin_dump_all()