<script setup lang="ts">
import { nextTick, ref } from 'vue'

interface IPost {
  id: number,
  tags: string,
  file_url: string
}

interface ITagsCompleteItem {
  antecedent?: string,
  category: string,
  label: string,
  post_count: number,
  type: string,
  value: string
}

const tag_input = ref('')
const cookie_input = ref('')
const posts = ref([] as IPost[])
const isLoading = ref(false)

const img_column = ref(3)
const img_width = ref(250)
const img_opacity = ref(10)
const img_blur = ref(0)
const databaseName = ref('s')
const tags_complete_items = ref([] as ITagsCompleteItem[])
const el_taginput = ref<HTMLInputElement>()
const img_src_loaded = ref([] as IPost[])

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

async function search () {
  try {
    isLoading.value = true

    const res = await post_json(`/api/random/3`, {
      rating: databaseName.value,
      and_array: tag_input.value.split(' ').map(item => item.trim()),
      or_array: [],
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

async function search_random () {
  try {
    isLoading.value = true
    img_src_loaded.value = []
    posts.value = []

    for (let i = 0; i < 8; i++) {
      const res = await fetch(`/api/random/1?tags=${tag_input.value}&db=${databaseName.value}`)
      const [ row ] = await res.json()
      if (row) {
        posts.value.push(row)
        img_src_loaded.value.push(row)
      } else {
        break
      }
    }

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

async function copy_img_tags (post: IPost) {
  await navigator.clipboard.writeText(post.tags)

  alert(post.tags.slice(0, 100) + '...')
}

async function trigger_complete () {
  if (tag_input.value.length >= 2) {
    const input = tag_input.value.split(' ').pop() || ''
    const res = await fetch(`https://danbooru.donmai.us/autocomplete.json?search%5Bquery%5D=${encodeURIComponent(input)}&search%5Btype%5D=tag_query&version=1&limit=20`)
    const items = await res.json() as ITagsCompleteItem[]

    tags_complete_items.value = items
  } else {
    tags_complete_items.value = []
  }
}

async function input_complete (item: ITagsCompleteItem) {
  const tag_input_list = tag_input.value.split(' ')
  tag_input_list[tag_input_list.length - 1] = item.value
  tag_input.value = tag_input_list.join(' ') + ' '
  tags_complete_items.value = []

  await nextTick()
  el_taginput.value?.focus()
}

function back_top () {
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
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

</script>

<template>
  <div>

    <input ref="el_taginput" type="text" placeholder="tags" v-model="tag_input" style="width: 300px;" @input="trigger_complete">
    <select v-model="databaseName">
      <option value="s">Safe</option>
      <option value="e">Explicit</option>
    </select>
    column: <input type="number" v-model="img_column" min="0" max="10" />
    width: <input type="number" v-model="img_width" min="0" max="1000" />
    opacity:<input type="number" v-model="img_opacity" min="0" max="10" />
    blur:<input type="number" v-model="img_blur" min="0" max="100" />
  </div>

  <div>
    <input type="text" v-model="cookie_input" /><button @click="setSecureCookie('auth', cookie_input, 100)">set cookie</button>
  </div>

  <div v-if="tags_complete_items.length > 0" class="tags-complete">
    <div v-for="item in tags_complete_items" class="tags-complete-item" @click="input_complete(item)">
      <span v-if="item.antecedent">{{ item.antecedent }} -> </span>{{ item.label }}
    </div>
  </div>

  <div style="margin-top: 8px;">
    <button :disabled="isLoading" @click="search()" style="height: 30px;">Search</button>
    <button :disabled="isLoading" @click="search_random()" style="height: 30px;">Random</button>
    <button :disabled="isLoading" @click="search_question()" style="height: 30px;">Question</button>
  </div>

  <div class="img-container">
    <div v-for="post in img_src_loaded" :key="post.id" class="img-item" 
    :style="{ flex: `1 0 calc(100% / ${img_column})`, 'max-width': `calc(100% / ${img_column})` }">
      <img :src="`/api/image/${post.id}`"
           :style="{ opacity: img_opacity / 10, filter: `blur(${img_blur}px)`, 'width': `${img_width}px` }">

      <div class="links">
        <a href="javascript:;" @click="copy_img_tags(post)">copy</a>
        <a target="_blank" :href="`https://yande.re/post/show/${post.id}`" >open</a>
        <a target="_blank" :href="post.file_url" rel="noreferrer">raw</a>
        <input type="text" :value="post.id" @focus="select_all">
      </div>
    </div>
  </div>

  <div style="margin-top: 8px;">
    <button @click="back_top()" style="height: 30px;">Back Top Search</button>
  </div>
</template>

<style scoped>
.img-container .img-item img, .img-container .img-item video {
  height: auto;
  display: block;
  box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
}
.img-container .img-item {
  margin-bottom: 80px;
}
.img-container {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 12px;
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
