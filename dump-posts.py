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

pg_conn = psycopg2.connect("dbname=postgres user=dan", cursor_factory=RealDictCursor)
rating = 'e'

def getdb (dbname = 'images-tags.db'):
    conn = sqlite3.connect(dbname)
    conn.row_factory = sqlite3.Row
    return conn

lock = threading.Lock()

def get_last_id ():
   c = pg_conn.cursor()
   c.execute(f'SELECT MIN(id) as id from posts_{rating}')
   row = c.fetchone()
   c.close()
   return row['id']
   
def get_newest_id ():
   c = pg_conn.cursor()
   c.execute(f'SELECT MAX(id) as id from posts_{rating}')
   row = c.fetchone()
   c.close()
   return row['id']

def get_post (id):
    c = pg_conn.cursor()

    c.execute(f'SELECT * FROM posts_{rating} where id = %s', (id,))
    row = c.fetchone()
    c.close()

    return row

def add_post (post):
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

    post = get_post(id)

    if (post is not None):
       return

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
        sample_data = res.read()
        break
      except Exception as e:
        print(e)
        continue
    
    image_stream = BytesIO(sample_data)
    image = Image.open(image_stream)

    tags = app.image_to_wd14_tags(image, 'wd14-convnext', 0.35, False, True, False, True)

    with lock:
      with getdb('images-data.db') as conn_data:
        c = pg_conn.cursor()

        c.execute(f'INSERT INTO posts_{rating} (id, file_ext, sample_url, file_url, sample_width, sample_height, score, updated_at, tags) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)', 
                  (id, file_ext, sample_url, file_url, sample_width, sample_height, score, updated_at, tags))
        
        tag_list = tags.split(',')

        for tag in tag_list:
          t = tag.strip()
          c.execute(f'SELECT id from tags_{rating} where tag = %s', (t,))
          row = c.fetchone()
          
          if row is None:
             c.execute(f'INSERT INTO tags_{rating} (tag) values (%s) RETURNING id;', (t,))
             row = c.fetchone()
          
          c.execute(f'INSERT INTO post_tag_{rating} (post_id, tag_id) values (%s, %s)', (id, row['id']))

        c2 = conn_data.cursor()
        c2.execute('DELETE FROM images where id = ?', (id,))
        c2.execute('INSERT INTO images (id, data) VALUES (?, ?)', (id, sample_data))
        
        c.close()
        pg_conn.commit()
        c2.close()
        conn_data.commit()

    return id

def add_post_task (post):
   id = post['id']
   
   with lock:
      print(f'begin {id}')
   
   return add_post(post)

def begin_dump (tags):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'}
    less_id = get_last_id()

    while True:
      if (less_id is None):
        less_id = 99999999
        
      url = 'https://yande.re/post.json'
      params = { 'tags': tags + f' id:<{less_id}' }
      response = requests.get(url, params=params,  headers=headers)
      data = response.json()

      with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(add_post_task, data)

        for r in results:
          if r < less_id:
             less_id = r
          print(f'done: {r}')

def begin_dump_new (tags):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'}
    newest_id = get_newest_id()

    while True:

      url = 'https://yande.re/post.json'
      params = { 'tags': tags + f' id:>{newest_id} order:id' }
      response = requests.get(url, params=params,  headers=headers)
      data = response.json()

      if (len(data) == 0):
         break

      with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(add_post_task, data)

        for r in results:
          if r > newest_id:
             newest_id = r
          print(f'done: {r}')

def split_image_data ():
   with getdb() as conn1, getdb('images-data.db') as conn2:
      c1 = conn1.cursor()
      c2 = conn2.cursor()

      c1.execute('SELECT id FROM images')
      rows1 = c1.fetchall()

      for row1 in rows1:
         id = row1['id']
         c1.execute('SELECT data FROM images where id = ?', (id,))
         data = c1.fetchone()['data']

         c2.execute('INSERT INTO images (id, data) VALUES (?,?)', (id, data))
      conn2.commit()

# begin_dump('rating:s')
begin_dump_new('rating:e')
# split_image_data()
