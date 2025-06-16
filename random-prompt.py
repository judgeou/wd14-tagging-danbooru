from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from PIL import Image
import psycopg2
from psycopg2.extras import RealDictCursor
import clipboard
import random
import json

def getdb_pg ():
    return psycopg2.connect("dbname=postgres user=dan", cursor_factory=RealDictCursor)

def random_next (tag: str, pg_conn: psycopg2.extensions.connection, used_tags: set):
    sqlstr = '''
    WITH related_posts AS (
        select post_id from post_tag_s 
        where tag_id = (select id from tags_s where tag = %s)
        order by random()
        limit 100
    )
    select tag_id, tags_s.tag 
    from post_tag_s 
    inner join tags_s on tags_s.id = tag_id
    where post_id in (select post_id from related_posts)
    and tags_s.tag <> ALL(%s)  -- 排除所有已使用的tags
    order by random()
    limit 2
    '''

    c = pg_conn.cursor()
    c.execute(sqlstr, (tag, list(used_tags)))
    results = c.fetchall()
    c.close()
    return [r['tag'] for r in results] if results else None

def random_prompt (n: int, first_tag: str = '1girl'):
    with getdb_pg() as pg_conn:
        tags = set([first_tag])
        current_tag = first_tag
        
        while len(tags) < n + 1:
            new_tags = random_next(current_tag, pg_conn, tags)
            if not new_tags:  # 如果找不到新的相关tag，就从已有tags中随机选择一个作为current_tag
                current_tag = random.choice(list(tags))
                continue
            
            for tag in new_tags:
                if len(tags) < n + 1:  # 确保不会超过要求的数量
                    tags.add(tag)
            
            current_tag = new_tags[-1]  # 使用最后一个新tag作为下一次查询的基础
            
        return list(tags)
    
def random_prompt_2 (n: int, first_tag: str = '1girl'):
    with getdb_pg() as pg_conn:
        c = pg_conn.cursor()
        c.execute('select tag from tags_s where tag <> %s and tag_count > 10 order by random() limit %s', (first_tag, n))
        tags = [r['tag'] for r in c.fetchall()]
        c.close()
        tags.insert(0, first_tag)
        return tags
    
def random_prompt_3 (n: int, first_tag: str = '1girl'):
    category = 0
    with getdb_pg() as pg_conn:
        c = pg_conn.cursor()
        c.execute('''SELECT name FROM dan.tags_danbooru
WHERE is_deprecated = false and category = %s and post_count > 2000 and name not like '%%(cosplay)%%' and name not like '%%penis%%'
order by random()
limit %s''', (category, n))
        tags = [r['name'] for r in c.fetchall()]
        c.close()
        tags.insert(0, first_tag)
        return tags
    
def import_danbooru_tags ():
    with getdb_pg() as pg_conn:
        with open('./tags/tags.json', 'r', encoding='utf-8') as file, pg_conn.cursor() as c:
            for line in file:
                tag_data = json.loads(line)
                name = tag_data['name'][:255]
                c.execute('''
                    INSERT INTO tags_danbooru (id, name, post_count, category, created_at, updated_at, is_deprecated, words)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        post_count = EXCLUDED.post_count,
                        category = EXCLUDED.category,
                        created_at = EXCLUDED.created_at,
                        updated_at = EXCLUDED.updated_at,
                        is_deprecated = EXCLUDED.is_deprecated,
                        words = EXCLUDED.words
                ''', (
                    tag_data['id'],
                    name,
                    tag_data['post_count'],
                    tag_data['category'],
                    tag_data['created_at'],
                    tag_data['updated_at'],
                    tag_data['is_deprecated'],
                    tag_data['words']
                ))
            pg_conn.commit()

while True: 
    tags = random_prompt_3(40, '1girl')
    tags_str = ', '.join(tags).replace('_', ' ').replace('(', '\\(').replace(')', '\\)')
    print(tags_str)
    clipboard.copy(tags_str)
    input('enter to continue')
