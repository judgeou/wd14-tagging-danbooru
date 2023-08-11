<script setup lang="ts">
import { nextTick, ref } from 'vue'

interface IPost {
  id: number,
  tags: string
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
const posts = ref([] as IPost[])
const isLoading = ref(false)

const img_opacity = ref(10)
const tags_complete_items = ref([] as ITagsCompleteItem[])
const el_taginput = ref<HTMLInputElement>()
const img_src_loaded = ref([] as IPost[])

async function search () {
  try {
    isLoading.value = true

    const res = await fetch(`/api/random?tags=${tag_input.value}`)
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
}

</script>

<template>
  <div>

    <input ref="el_taginput" type="text" placeholder="tags" v-model="tag_input" style="width: 300px;" @input="trigger_complete">
    opacity:<input type="number" v-model="img_opacity" min="0" max="10" />
  </div>

  <div v-if="tags_complete_items.length > 0" class="tags-complete">
    <div v-for="item in tags_complete_items" class="tags-complete-item" @click="input_complete(item)">
      <span v-if="item.antecedent">{{ item.antecedent }} -> </span>{{ item.label }}
    </div>
  </div>

  <div style="margin-top: 8px;">
    <button :disabled="isLoading" @click="search()" style="height: 30px;">Search</button>
  </div>

  <div class="img-container">
    <div v-for="post in img_src_loaded" :key="post.id" class="img-item">
      <img :src="`/api/image/${post.id}`"
           :style="{ opacity: img_opacity / 10 }">

      <div class="links">
        <a href="javascript:;" @click="copy_img_tags(post)">copy</a>
        <a target="_blank" :href="`https://yande.re/post/show/${post.id}`">open</a>
      </div>
    </div>
  </div>

  <div style="margin-top: 8px;">
    <button @click="back_top()" style="height: 30px;">Back Top</button>
  </div>
</template>

<style scoped>
.img-container .img-item img, .img-container .img-item video {
  width: 250px;
  height: auto;
  display: block;
  box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
}
.img-container .img-item {
  flex: 1 0 calc(100% / 3);
  max-width: calc(100% / 3);
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
