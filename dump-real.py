import os
from concurrent.futures import ThreadPoolExecutor
import threading
from io import BytesIO
from PIL import Image
import app
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from datetime import datetime

import_dir = './real-import'
lock = threading.Lock()

def read_file (file_path: str):
  try:
    with open(file_path, "rb") as file:
      file_contents = file.read()
      return file_contents
  except FileNotFoundError:
    print(f"The file {file_path} was not found.")
  except Exception as e:
    print(f"An error occurred: {str(e)}")

def bytes_to_bit_data_literal(byte_data):
    # Convert each byte to its binary representation and concatenate them
    binary_string = ''.join(format(byte, '08b') for byte in byte_data)
    # Create the binary string literal
    bit_data_literal = f"B'{binary_string}'"
    return bit_data_literal

def has_nsfw_tag (tag_arr: list[str]):
   nsfw_tag_list = ['nipples', 'pussy', 'monochrome', 'female_pubic_hair', 'nude', 'penis']
   for tag in tag_arr:
      tag_s = tag.strip()
      for nsfw_tag in nsfw_tag_list:
         if tag_s == nsfw_tag:
            return True
         
   return False

def dump_dir (image_files: list[str], extra_tag = None):
  with psycopg2.connect("dbname=postgres user=real", cursor_factory=RealDictCursor) as pg_conn:
    c = pg_conn.cursor()
    c.execute(f"select nextval('batch_id_seq') as batch_id")
    batch_id = c.fetchone()['batch_id']
    c.execute('BEGIN')

    def dump_file (image_file: str):
      image_data = read_file(image_file)
      sha256 = hashlib.sha256(image_data).hexdigest()
      c = pg_conn.cursor()

      c.execute(f'select id,data from image_data where sha256 = %s', (sha256, ))
      row = c.fetchone()

      if row is None:
        image = Image.open(BytesIO(image_data))
        
        if image.width > image.height:
          image = image.resize((1920, int(image.height / image.width * 1920)), resample=Image.BICUBIC)
        else:
          image = image.resize((int(image.width / image.height * 1920), 1920), resample=Image.BICUBIC)
        
        bio = BytesIO()
        image.save(bio, format='webp', quality=85)
        c.execute('INSERT INTO image_data (data, sha256) VALUES (%s,%s) RETURNING id;', (bio.getvalue(), sha256))
        row = c.fetchone()
      else:
        image = Image.open(BytesIO(row['data']))

      id = row['id']
      
      with lock:
        tags = app.image_to_wd14_tags(image, 'wd14-convnext', 0.35, False, True, False, True)
      
      tag_list = tags.split(',')

      if extra_tag != 'unknow':
        tag_list.append(extra_tag)
      
      tag_list = list(set(tag_list))
      isNSFW = has_nsfw_tag(tag_list)
      rating = 'e' if isNSFW else 's'

      with lock:
        c.execute('SELECT * from posts_real where id = %s', (id, ))
        post = c.fetchone()

        if post is None:
          file_ext = os.path.splitext(image_file)[1]
          updated_at = int(datetime.now().timestamp())
          c.execute('INSERT INTO posts_real (id, file_ext, sample_width, sample_height, updated_at, tags, rating, artist, batch_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (id, file_ext, image.width, image.height, updated_at, tags, rating, extra_tag, batch_id))
          
        c.execute(f'DELETE FROM post_tag_real where post_id = %s', (id,))

        for tag in tag_list:
          t = tag.strip()
          c.execute(f'SELECT id from tags_real where tag = %s', (t,))
          row = c.fetchone()

          if row is None:
            c.execute(f'INSERT INTO tags_real (tag) values (%s) RETURNING id;', (t,))
            row = c.fetchone()

          c.execute(f'INSERT INTO post_tag_real (post_id, tag_id) values (%s, %s) ON CONFLICT (post_id, tag_id) DO NOTHING', (id, row['id']))

      # print(f'done {id} {rating}')
      c.close()
      return id

    with ThreadPoolExecutor(max_workers=4) as tpe:
      results = tpe.map(dump_file, image_files)
      for r in results:
        print(r)

    pg_conn.commit()
    c.close()


def begin_dump_all ():
  dir_list = os.listdir(import_dir)
  
  for dir in dir_list:
    dir_path = os.path.join(import_dir, dir)
    
    if os.path.isdir(dir_path):
      image_files = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.endswith(".jpg") or f.endswith(".jpeg") or f.endswith(".png")]
      dump_dir(image_files, dir)

      for image_file in image_files:
        os.remove(image_file)


while True:
  begin_dump_all()
  input('enter for next run')