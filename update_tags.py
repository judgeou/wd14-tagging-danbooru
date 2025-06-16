import sqlite3
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import threading
import io
from io import BytesIO
from PIL import Image
import requests
import app
import psycopg2
from psycopg2.extras import RealDictCursor

lock = threading.Lock()

def getdb (dbname = 'images-data.db'):
    conn = sqlite3.connect(dbname)
    conn.row_factory = sqlite3.Row
    return conn

def getdb_pg ():
    return psycopg2.connect("dbname=postgres user=dan", cursor_factory=RealDictCursor)

def update_tags ():
    with getdb_pg() as pg_conn, getdb() as db_conn:
        current_id = 910516
        while True:
            c1 = pg_conn.cursor()
            c2 = db_conn.cursor()
            try:
                c2.execute(f'SELECT id, data FROM images WHERE id < ? order by id desc limit 10', (current_id,))
                rows = c2.fetchall()
                if len(rows) == 0:
                    break

                for row in rows:
                    id = row['id']
                    current_id = id if id < current_id else current_id

                    c1.execute(f'SELECT id FROM posts_s where id = %s limit 1', (id,))
                    row_s = c1.fetchone()

                    c1.execute(f'SELECT id FROM posts_e where id = %s limit 1', (id,))
                    row_e = c1.fetchone()

                    if row_s is None and row_e is None:
                        continue

                    data = row['data']
                    image = Image.open(io.BytesIO(data))
                    tags, tags_character = app.image_to_wd14_tags(image, 'wd-eva02-large-tagger-v3', 0.35, False, True, False, True)
                    tag_list = tags.split(',')
                    tag_list_character = tags_character.split(',')
                    
                    # 限制 tags_character 长度不超过 256
                    if len(tags_character) > 256:
                        # 从后往前截取标签，直到总长度不超过 256
                        truncated_tags = []
                        current_length = 0
                        for tag in tag_list_character:
                            tag = tag.strip()
                            if current_length + len(tag) + 1 <= 256:  # +1 是为了考虑逗号
                                truncated_tags.append(tag)
                                current_length += len(tag) + 1
                            else:
                                break
                        tags_character = ','.join(truncated_tags)
                    
                    rating_flag = 's' if row_s is not None else 'e'

                    c1.execute('BEGIN')
                    c1.execute(f'UPDATE posts_{rating_flag} set tags = %s, tags_character = %s where id = %s', (tags, tags_character, id))
                    c1.execute(f'DELETE FROM post_tag_{rating_flag} where post_id = %s', (id,))

                    for tag in tag_list:
                        t = tag.strip()
                        c1.execute(f'SELECT id from tags_{rating_flag} where tag = %s', (t,))
                        row = c1.fetchone()

                        if row is None:
                            c1.execute(f'INSERT INTO tags_{rating_flag} (tag) values (%s) RETURNING id;', (t,))
                            row = c1.fetchone()

                        c1.execute(f'INSERT INTO post_tag_{rating_flag} (post_id, tag_id) values (%s, %s) ON CONFLICT (post_id, tag_id) DO NOTHING', (id, row['id']))

                    c1.execute('COMMIT')
                    print(f'{id} done')

                # pg_conn.commit()
                print('DONE')
            finally:
                c1.close()
                c2.close()

update_tags()