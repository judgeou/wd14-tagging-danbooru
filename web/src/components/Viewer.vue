<script setup lang="ts">
import { nextTick, ref, watch, Ref, onMounted, onUnmounted } from 'vue'

interface IPost {
  id: number,
  tags: string,
  file_url: string,
  tags_yande: string,
  link?: string
}

interface ITagsCompleteItem {
  tag: string,
  tag_zh: string
}

const MAX_PAGE_ID = 91205996

const tag_input = ref('')
const tag_input_or_1 = ref('')
const tag_input_or_2 = ref('')
const tag_input_not_1 = ref('')
const score = ref(0)
const tablesample = ref(1)
const min_id = ref(0)

const page_begin_id_s = ref(load_from_localstorage('page_begin_id_s', 0)); watch_save_to_localstorage('page_begin_id_s', page_begin_id_s)
const page_end_id_s = ref(load_from_localstorage('page_end_id_s', MAX_PAGE_ID)); watch_save_to_localstorage('page_end_id_s', page_end_id_s)
const page_begin_id_e = ref(load_from_localstorage('page_begin_id_e', 0)); watch_save_to_localstorage('page_begin_id_e', page_begin_id_e)
const page_end_id_e = ref(load_from_localstorage('page_end_id_e', MAX_PAGE_ID)); watch_save_to_localstorage('page_end_id_e', page_end_id_e)

const cookie_input = ref('')
const exclude_input = ref(load_from_localstorage('exclude_input', '') as string)
const posts = ref([] as IPost[])
const isLoading = ref(false)
const alertCopy = ref(false)

const column_gap = ref(load_from_localstorage('column_gap', 256))
const img_column = ref(load_from_localstorage('img_column', 3))
const img_opacity = ref(load_from_localstorage('img_opacity', 3))
const img_blur = ref(0)
const databaseName = ref('s')
const tags_complete_items = ref([] as ITagsCompleteItem[])
const el_taginput = ref<HTMLInputElement>()
const img_src_loaded = ref([] as IPost[])
const observer = ref<IntersectionObserver | null>(null)
const loadedImages = ref(new Set<number>())

watch_save_to_localstorage('column_gap', column_gap)
watch_save_to_localstorage('img_column', img_column)
watch_save_to_localstorage('img_opacity', img_opacity)
watch_save_to_localstorage('exclude_input', exclude_input)

function load_from_localstorage (name: string, defaultValue: any) {
  return localStorage.getItem('DAN_VIEWER_' + name) || defaultValue
}

function watch_save_to_localstorage (name: string, ref_obj: Ref) {
  watch(ref_obj, newValue => {
    localStorage.setItem('DAN_VIEWER_' + name, newValue.toString())
  })
}

async function post_json (path: string, data: any) {
  const headers = {
    'Content-Type': 'application/json'
  };

  const res = await fetch(path, {
    method: 'POST',
    headers,
    body: JSON.stringify(data)
  })

  return res.json()
}

async function search (url = `/api/random/3`, action = 'search') {
  try {
    isLoading.value = true
    loadedImages.value.clear()
    let limit = 50

    if (action != 'search') {
      limit = img_column.value
    }

    const page_begin_id = databaseName.value === 's' ? page_begin_id_s : page_begin_id_e
    const page_end_id = databaseName.value === 's' ? page_end_id_s : page_end_id_e

    const data = {
      rating: databaseName.value,
      score: score.value,
      tablesample: action === 'search' ? tablesample.value : 100,
      and_array: tag_input.value.split(' ').map(item => item.trim()),
      or_array: [ tag_input_or_1.value, tag_input_or_2.value ].filter(t => t.trim()).map(t => t.split(' ')),
      not_array: [ tag_input_not_1.value ].filter(t => t.trim()).map(t => t.split(' ')),
      limit,
      page_begin_id: page_begin_id.value,
      page_end_id: page_end_id.value,
      action,
      until_id: min_id.value
    }

    const res = await post_json(url, data)
    posts.value = res

    if (action != 'search') {
      page_begin_id.value = posts.value.reduce((min, post) => Math.min(min, post.id), MAX_PAGE_ID)
      page_end_id.value = posts.value.reduce((max, post) => Math.max(max, post.id), 0)
    } else if (action === 'search') {
      min_id.value = posts.value.reduce((min, post) => Math.min(min, post.id), MAX_PAGE_ID)
    }
    
    img_src_loaded.value = posts.value
  } catch (e) {
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

async function search_question () {
  try {
    isLoading.value = true

    const res = await fetch(`/api/random/q?tags=${tag_input.value}`)
    posts.value = await res.json()
    
    img_src_loaded.value = posts.value
  } catch (e) {
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

async function copy_img_tags (post: IPost, is_space_split = false, $event: MouseEvent, is_random_pick = false, pick_count = -1) {
  const exclude_set = new Set(exclude_input.value.split(',').map(tag => tag.trim()))
  let tags_arr =  post.tags.split(',').map(tag => tag.trim())

  const censored_tags = ['censored', 'bar_censor', 'mosaic_censoring', 'pointless_censoring']
  const has_censored_tag = tags_arr.some(tag => censored_tags.indexOf(tag) != -1)
  tags_arr = tags_arr.filter(tag => censored_tags.indexOf(tag) == -1).map(tag => tag.replace(/(small_breasts|flat_chest)/, 'large_breasts'))

  if (has_censored_tag) {
    tags_arr.push('uncensored')
  }

  if (is_random_pick) {
    tags_arr = shuffleArray(tags_arr).slice(0, pick_count < 0 ? tags_arr.length : pick_count)

    if (!tags_arr.includes('1girl')) {
      tags_arr.unshift('1girl')
    }
  }

  const tags_yande = $event.altKey ? post.tags_yande.split(' ').map(tag => tag.replace(/\(/g, '\\(').replace(/\)/g, '\\)')) : []

  const copyTags =  
    [...new Set([...tags_yande, ...tags_arr])]
    .filter(tag => !exclude_set.has(tag))
    .map(t => t.replace(/_/g, ' '))
    .join(is_space_split ? ' ' : ', ')
  await navigator.clipboard.writeText(copyTags)

  console.log(copyTags)
  alertCopy.value = true
  await new Promise(r => setTimeout(r, 1000))
  alertCopy.value = false
}

async function copy_img_tags_wd14 (post: IPost) {
  alertCopy.value = true
  const res = await fetch(`/api/image/${post.id}/wd14`)
  const tags = await res.text()

  await navigator.clipboard.writeText(tags)
  console.log(tags)
  alertCopy.value = false
}

async function copy_img_tags_wd14_and (post: IPost, count = 24) {
  alertCopy.value = true
  const res = await fetch(`/api/image/${post.id}/wd14`)
  const exclude = ['white background', 'simple background', 'blurry']
  const t1 = shuffleArray((await res.text()).split(',').filter(tag => exclude.indexOf(tag.trim()) == -1))
  // const haflen = 1
  // const fixed_tags = t1.slice(0, haflen).map(tag => tag.trim()).join(' and ')
  const transition_tags = t1.slice(0, count).map((tag) => `${tag.trim()}`).join(', ')
  
  const tags = `${transition_tags}`

  await navigator.clipboard.writeText(tags)
  console.log(tags)
  alertCopy.value = false
}

async function trigger_complete () {
  if (tag_input.value.length >= 2) {
    const input = tag_input.value.split(' ').pop() || ''
    const res = await fetch(`/api/search/tag?tag=${input}`)
    const items = await res.json() as ITagsCompleteItem[]

    tags_complete_items.value = items
  } else {
    tags_complete_items.value = []
  }
}

async function input_complete (item: ITagsCompleteItem) {
  const tag_input_list = tag_input.value.split(' ')
  tag_input_list[tag_input_list.length - 1] = item.tag
  tag_input.value = tag_input_list.join(' ') + ' '
  tags_complete_items.value = []

  await nextTick()
  el_taginput.value?.focus()
}

function back_top () {
  window.scrollTo({
    top: 0,
    behavior: 'instant'
  })
}

function setSecureCookie (name: string, value: string, daysToExpire: number) {
  const expirationDate = new Date();
  expirationDate.setDate(expirationDate.getDate() + daysToExpire);

  const cookieValue = encodeURIComponent(name) + '=' + encodeURIComponent(value) + '; expires=' + expirationDate.toUTCString() + '; path=/; Secure';

  document.cookie = cookieValue;
}

function shuffleArray<T> (array_: T[]) {
  const array = [...array_]
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
  return array
}

function handleImgRef(el: HTMLImageElement | null) {
  if (el && observer.value) {
    observer.value.observe(el)
  }
}

onMounted(() => {
  observer.value = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target as HTMLImageElement
        const postId = Number(img.dataset.postId)
        if (true) {
          img.src = img.dataset.src || 'about:blank'
          loadedImages.value.add(postId)
        }
      }
    })
  }, {
    rootMargin: '50px 0px'
  })
})

onUnmounted(() => {
  observer.value?.disconnect()
})
</script>

<template>
  <div>

    <input ref="el_taginput" type="text" placeholder="tags" v-model="tag_input" style="width: 200px;" @input="trigger_complete">
    <input type="text" placeholder="tags or 1" v-model="tag_input_or_1" style="width: 300px;">
    <!-- <input type="text" placeholder="tags or 2" v-model="tag_input_or_2" style="width: 100px;"> -->
    <input type="number" placeholder="until id" v-model="min_id" style="width: 100px;">
    <input type="text" placeholder="tags not 1" v-model="tag_input_not_1" style="width: 100px">
    <input type="text" placeholder="score" v-model="score" style="width: 50px;">
    <input type="text" placeholder="tablesample" v-model="tablesample" style="width: 50px;">
    <select v-model="databaseName">
      <option value="s">Safe</option>
      <option value="e">Explicit</option>
    </select>
    column: <input type="number" v-model="img_column" min="0" max="10" />
    column_gap: <input type="number" v-model="column_gap" min="0" max="1000">

    opacity:<input type="number" v-model="img_opacity" min="0" max="10" />
    blur:<input type="number" v-model="img_blur" min="0" max="100" />
  </div>

  <div>
    <input type="text" v-model="exclude_input" placeholder="exclude tags">
  </div>

  <div>
    <input type="text" v-model="cookie_input" /><button @click="setSecureCookie('auth', cookie_input, 100)">set cookie</button>
  </div>

  <div v-if="tags_complete_items.length > 0" class="tags-complete">
    <div v-for="item in tags_complete_items" class="tags-complete-item" @click="input_complete(item)">
      {{ item.tag }} <span v-if="item.tag_zh">{{ item.tag_zh }}</span>
    </div>
  </div>

  <div style="margin-top: 8px; display: flex; gap: 16px;">
    <div style="height: 30px; display: flex;">
      <button :disabled="isLoading" @click="search()">Search</button>
      <button :disabled="isLoading" @click="search('/api/random/4')">Search2</button>
      <button :disabled="isLoading" @click="search_question()">Question</button>
    </div>

    <div style="height: 30px; display: flex;">
      <button :disabled="isLoading" @click="search('/api/random/3', 'newest')">newest</button>
      <button :disabled="isLoading" @click="search('/api/random/3', 'next')">next page</button>
      <button :disabled="isLoading" @click="search('/api/random/3', 'prev')">prev page</button>
      <button :disabled="isLoading" @click="search('/api/random/3', 'oldest')">oldest</button>
      <input v-if="databaseName === 's'" type="text" v-model="page_begin_id_s" style="width: 100px;" />
      <input v-if="databaseName === 's'" type="text" v-model="page_end_id_s" style="width: 100px;" />
      <input v-if="databaseName === 'e'" type="text" v-model="page_begin_id_e" style="width: 100px;" />
      <input v-if="databaseName === 'e'" type="text" v-model="page_end_id_e" style="width: 100px;" />
    </div>
  </div>

  <div class="wf-container" :style="{ 'column-count': img_column, 'column-gap': `${column_gap}px` }">
    <div v-for="(post, index) in img_src_loaded" :key="post.id" class="wf-card" :style="{ 'margin-bottom': `${column_gap}px` }">
      <div class="links">
        <a href="javascript:;" @click="copy_img_tags(post, false, $event)">copy1</a>
        <!-- <a href="javascript:;" @click="copy_img_tags(post, false, $event, true, 15)">copy3</a> -->
        <a href="javascript:;" @click="copy_img_tags_wd14(post)">wd14</a>
        <a href="javascript:;" @click="copy_img_tags_wd14_and(post, 99)">wd14 space</a>
        <a href="javascript:;" @click="copy_img_tags_wd14_and(post)">wd14 and</a>
        <a target="_blank" :href="`https://yande.re/post/show/${post.id}`" >{{ post.id }}</a>
        <a target="_blank" :href="post.file_url" rel="noreferrer">raw</a>
      </div>
      <div v-if="alertCopy">
        copyed
      </div>
      
      <img
        v-if="index < 6"
        :src="post.link || `/api/image/${post.id}`"
        :style="{ opacity: img_opacity / 10, filter: `blur(${img_blur}px)`}"
        style="width: 100%;"
      />
      <img
        v-else
        :ref="(el) => handleImgRef(el as HTMLImageElement)"
        :data-src="post.link || `/api/image/${post.id}`"
        :data-post-id="post.id"
        :style="{ opacity: img_opacity / 10, filter: `blur(${img_blur}px)`}"
        style="width: 100%;"
        src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'%3E%3C/svg%3E"
      />
    </div>
  </div>

  <div style="margin-top: 8px;">
    <button @click="back_top()" style="height: 30px;">Back Top</button>
  </div>
</template>

<style scoped>
.wf-container {
  list-style: none;
  padding: 0;
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(v-bind(img_column), 1fr);
  gap: v-bind(column_gap)px;
}

.wf-card {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  transition: transform 0.2s ease;
}

.wf-card:hover {
  transform: translateY(-4px);
}

.wf-card img {
  box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
  width: 100%;
  height: auto;
  transition: all 0.3s ease;
  opacity: 0;
  animation: fadeIn 0.5s ease forwards;
  background: #f0f0f0;
  min-height: 100px;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: v-bind(img_opacity / 10);
    transform: translateY(0);
  }
}

.links a {
  margin-right: 8px;
}
.tags-complete {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
}
.tags-complete .tags-complete-item {
  margin-right: 8px;
  border: 1px solid #c7b2b2;
  padding: 2px;
  margin-bottom: 8px;
  cursor: pointer;
}
</style>
