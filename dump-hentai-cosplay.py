from concurrent.futures import ThreadPoolExecutor
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
import re
import hashlib
from io import BytesIO
from PIL import Image
import threading
import app
from datetime import datetime

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'}
baseUrl = 'https://zh.hentai-cosplays.com'
lock = threading.Lock()

def get_conn ():
  return psycopg2.connect("dbname=postgres user=real", cursor_factory=RealDictCursor)

def get_url_soup (url: str):
  response = requests.get(url,  headers=headers)
  htmlstr = response.text
  soup = BeautifulSoup(htmlstr, 'html.parser')
  return soup

def download_url (url: str):
  while True:
    try:
      response = requests.get(url,  headers=headers)
      image = Image.open(BytesIO(response.content))
      return image
    except:
      continue

def get_ext_url (url: str):
  return '.' + url.split('/')[-1].split('.')[-1]

def has_nsfw_tag (tag_arr: list[str]):
   nsfw_tag_list = ['nipples', 'pussy', 'monochrome', 'female_pubic_hair', 'nude', 'penis']
   for tag in tag_arr:
      tag_s = tag.strip()
      for nsfw_tag in nsfw_tag_list:
         if tag_s == nsfw_tag:
            return True
         
   return False

# response = requests.get('https://zh.hentai-cosplays.com/search',  headers=headers)
with get_conn() as pg_conn:
  c = pg_conn.cursor()
  c.execute('select * from dump_state')
  page = c.fetchone()['page']

  while True:
    page = page + 1
    soup = get_url_soup(f'{baseUrl}/search/page/{page}')
    li_list = soup.select('#image-list li')

    for li_item in li_list:
      a_item = li_item.select('.image-list-item-image a')[0]
      image_page_url = a_item.attrs['href']

      c.execute('select * from dump_url where url = %s', (image_page_url,))
      row = c.fetchone()

      if row is None:
        c.execute('BEGIN')
        c.execute(f"select nextval('batch_id_seq') as batch_id")
        batch_id = c.fetchone()['batch_id']
        image_page = 1

        def dump_image_url (image_url: str):
          try:
            image_url = re.sub('http://', 'https://', image_url)
            image = download_url(image_url)
            sha256 = hashlib.sha256(image.tobytes()).hexdigest()
            c = pg_conn.cursor()

            with lock:
              c.execute(f'select id,data from image_data where sha256 = %s', (sha256, ))
              row = c.fetchone()

              if row is None:            
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
            
            tag_list = list(set(tag_list))
            isNSFW = has_nsfw_tag(tag_list)
            rating = 'e' if isNSFW else 's'

            with lock:
              c.execute('SELECT * from posts_real where id = %s', (id, ))
              post = c.fetchone()

              if post is None:
                file_ext = get_ext_url(image_url)
                updated_at = int(datetime.now().timestamp())
                c.execute('INSERT INTO posts_real (id, file_ext, sample_width, sample_height, updated_at, tags, rating, artist, batch_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                  (id, file_ext, image.width, image.height, updated_at, tags, rating, None, batch_id))
                
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
          except Exception as e:
            pg_conn.rollback()
            print(e)
            exit(-1)

        while True:
          soup_page = get_url_soup(f'{baseUrl}{image_page_url}page/{image_page}')
          div_list = soup_page.select('#display_image_detail div.icon-overlay')
          image_url_list = []

          for div_item in div_list:
            img_item = div_item.select('img')[0]
            src = img_item.attrs['src']
            image_url = re.sub('p=\\d+/', '', src)
            image_url_list.append(image_url)

          if len(div_list) == 0:
            break

          with ThreadPoolExecutor(max_workers=10) as tpe:
            results = tpe.map(dump_image_url, image_url_list)
            for r in results:
              print(r)

          print(f'done image page {image_page}')
          image_page += 1

        c.execute('insert into dump_url (url) values (%s)', (image_page_url,))
        pg_conn.commit()
        print(f'commit {baseUrl}{image_page_url}')
      else:
        continue


    c.execute('update dump_state set page = %s', (page,))
    print(f'update page {page}')
