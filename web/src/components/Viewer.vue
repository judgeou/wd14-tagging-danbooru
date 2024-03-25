<script setup lang="ts">
import { nextTick, ref, watch, Ref } from 'vue'

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

const tag_input = ref('')
const tag_input_or_1 = ref('')
const tag_input_or_2 = ref('')
const tag_input_not_1 = ref('')
const score = ref(0)
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

async function search (url = `/api/random/3`) {
  try {
    isLoading.value = true

    const res = await post_json(url, {
      rating: databaseName.value,
      score: score.value,
      and_array: tag_input.value.split(' ').map(item => item.trim()),
      or_array: [ tag_input_or_1.value, tag_input_or_2.value ].filter(t => t.trim()).map(t => t.split(' ')),
      not_array: [ tag_input_not_1.value ].filter(t => t.trim()).map(t => t.split(' ')),
      limit: 20
    })
    posts.value = res
    
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

async function copy_img_tags (post: IPost, is_space_split = false, $event: MouseEvent, is_random_pick = false) {
  const exclude_set = new Set(exclude_input.value.split(',').map(tag => tag.trim()))
  let tags_arr =  post.tags.split(',').map(tag => tag.trim())

  if (is_random_pick) {
    tags_arr = shuffleArray(tags_arr).slice(0, 30)

    if (!tags_arr.includes('1girl')) {
      tags_arr.unshift('1girl')
    }
  }

  const copyTags = (($event.ctrlKey || $event.metaKey) ? `${post.tags_yande}, ` : '') 
    + tags_arr
    .filter(tag => !exclude_set.has(tag))
    .map(t => t.replace(/_/g, ' '))
    .join(is_space_split ? ' ' : ', ')
  await navigator.clipboard.writeText(copyTags)

  console.log(copyTags)
  alertCopy.value = true
  await new Promise(r => setTimeout(r, 1000))
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

  search()
}

function select_all (e: FocusEvent) {
  const el = e.target as HTMLInputElement
  el.select()
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
</script>

<template>
  <div>

    <input ref="el_taginput" type="text" placeholder="tags" v-model="tag_input" style="width: 300px;" @input="trigger_complete">
    <input type="text" placeholder="tags or 1" v-model="tag_input_or_1" style="width: 100px;">
    <input type="text" placeholder="tags or 2" v-model="tag_input_or_2" style="width: 100px;">
    <input type="text" placeholder="tags not 1" v-model="tag_input_not_1" style="width: 100px">
    <input type="text" placeholder="score" v-model="score" style="width: 100px;">
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

  <div style="margin-top: 8px;">
    <button :disabled="isLoading" @click="search()" style="height: 30px;">Search</button>
    <button :disabled="isLoading" @click="search('/api/random/4')" style="height: 30px;">Search2</button>
    <button :disabled="isLoading" @click="search_question()" style="height: 30px;">Question</button>
  </div>

  <div class="wf-container" :style="{ 'column-count': img_column, 'column-gap': `${column_gap}px` }">
    <div v-for="post in img_src_loaded" :key="post.id" class="wf-card" :style="{ 'margin-bottom': `${column_gap}px` }">
      <img
      :src="post.link || `/api/image/${post.id}`"
      :style="{ opacity: img_opacity / 10, filter: `blur(${img_blur}px)`}"
      style="width: 100%;" />

      <div class="links">
        <a href="javascript:;" @click="copy_img_tags(post, false, $event)">copy1</a>
        <a href="javascript:;" @click="copy_img_tags(post, true, $event)">copy2</a>
        <a href="javascript:;" @click="copy_img_tags(post, false, $event, true)">copy3</a>
        <a target="_blank" :href="`https://yande.re/post/show/${post.id}`" >open</a>
        <a target="_blank" :href="post.file_url" rel="noreferrer">raw</a>
        <input type="text" :value="`hqyt ${post.id}`" @focus="select_all">
      </div>
      <div v-if="alertCopy">
        copyed
      </div>

      <div>
        {{ post.tags_yande }}
      </div>
    </div>
  </div>

  <div style="margin-top: 8px;">
    <button @click="back_top()" style="height: 30px;">Back Top Search</button>
  </div>
</template>

<style scoped>
.wf-container {
  list-style: none;
  padding: 0;
}
.wf-card {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  break-inside: avoid;
}
.wf-card img {
  box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
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
