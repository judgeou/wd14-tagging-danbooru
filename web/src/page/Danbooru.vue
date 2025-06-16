<template>
  <div class="flex">
    <select v-model="selectedApi">
      <option value="danbooru">Danbooru</option>
      <option value="gelbooru">Gelbooru</option>
    </select>
    
    <input type="text" v-model="tag_input" placeholder="tag (使用 | 分隔实现OR搜索)" style="width: 300px;">

    <input type="date" v-model="before_date">
    <input type="number" v-model="page_map[tag_input]" style="width: 60px;">
    <input type="number" v-model="columnWidth" placeholder="列宽(px)" min="100">
  </div>

  <div class="flex">
    <button :disabled="loading" @click="search('newest')">newest</button>
    <button :disabled="loading" @click="search('current')">current</button>
    <button :disabled="loading" @click="search('left')">←left</button>
    <button :disabled="loading" @click="search('right')">right→</button>
  </div>

  <div v-if="isOrSearch" class="or-search-info">
    正在进行OR搜索，合并多个条件的结果...
  </div>

  <div class="image-grid">
    <div v-for="post in posts" :key="post.id" class="image-item" @click="click_post(post, $event)">
      <img v-if="['mp4', 'zip'].indexOf(post.file_ext) == -1 && post.large_file_url" :src="post.large_file_url" :alt="post.id" loading="lazy" :class="{ 'blur': post.rating === 'e', 'shake': post.id === copiedId }">
      <video v-if="['mp4', 'zip'].indexOf(post.file_ext) >= 0 && post.file_url" :src="post.file_url"
        :alt="post.id"
        controls
        loading="lazy"
        muted
        loop
        :class="{ 'blur': post.rating === 'e', 'shake': post.id === copiedId }"
        @mouseenter="on_mouse_enter"
        @mouseleave="on_mouse_leave"></video>
      <a   
         class="post-id-link" 
         target="_blank"
         @click.stop>{{post.id}}</a>
    </div>
  </div>

  <div class="flex">
    <button :disabled="loading" @click="search('left')">←left</button>
    <button :disabled="loading" @click="search('right')">right→</button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, Ref, onMounted } from 'vue'

const limit = 20

const tag_input = ref(load_from_localstorage_json('tag_input', '1girl')); watch_save_to_localstorage('tag_input', tag_input)
const page_map = ref<Record<string, number>>({});
const before_date = ref(load_from_localstorage('before_date', '2024-12-15')); watch_save_to_localstorage('before_date', before_date)
const posts = ref<any[]>([])
const loading = ref(false)

// 添加新的ref用于跟踪最近复制的图片
const copiedId = ref<number | null>(null)

const columnWidth = ref(300)

// 添加OR搜索状态
const isOrSearch = ref(false)

// 添加 API 选择
const selectedApi = ref(load_from_localstorage('selected_api', 'danbooru')); 
watch_save_to_localstorage('selected_api', selectedApi)

async function search(direction: string) {
  loading.value = true

  let tags = tag_input.value
  let page_map_value = {...page_map.value}
  let page = page_map_value[tag_input.value] || 1

  if (direction == 'left') {
    page -= 1
  } else if (direction == 'right') {
    page += 1
  } else if (direction == 'current') {
    // page.value = 1
  } else {
    page = 1
  }

  // 检查是否包含 OR 逻辑（使用 | 分隔符）
  const tagGroups = tags.split('|').map((group: string) => group.trim()).filter((group: string) => group.length > 0)
  
  let allRows: any[] = []
  
  // 更新OR搜索状态
  isOrSearch.value = tagGroups.length > 1
  
  if (tagGroups.length > 1) {
    // OR 逻辑：并行发送多个请求
    const requests = tagGroups.map(async (tagGroup: string) => {
      const qs = new URLSearchParams()
      let apiUrl
      
      if (selectedApi.value === 'danbooru') {
        qs.set('limit', limit.toString())
        qs.set('tags', tagGroup)
        qs.set('page', page.toString())
        apiUrl = `https://danbooru.donmai.us/posts.json?${qs.toString()}`
      } else {
        // Gelbooru API
        qs.set('page', 'dapi')
        qs.set('s', 'post')
        qs.set('q', 'index')
        qs.set('json', '1')
        qs.set('limit', limit.toString())
        qs.set('pid', (page - 1).toString())
        qs.set('tags', tagGroup)
        apiUrl = `/api/gelbooru/posts?${qs.toString()}`
      }
      
      try {
        const res = await fetch(apiUrl)
        const data = await res.json()
        return selectedApi.value === 'danbooru' ? data : data.post
      } catch (error) {
        console.error(`搜索标签 "${tagGroup}" 时出错:`, error)
        return []
      }
    })
    
    // 等待所有请求完成
    const results = await Promise.all(requests)
    
    // 合并所有结果
    const allPosts = results.flat()
    
    // 按ID去重
    const uniquePosts = allPosts.filter((post, index, self) => 
      index === self.findIndex(p => p.id === post.id)
    )
    
    // 按ID排序（最新的在前）
    uniquePosts.sort((a, b) => b.id - a.id)
    
    // 限制结果数量
    allRows = uniquePosts.slice(0, limit * tagGroups.length)
    
  } else {
    // 单个搜索条件，使用原有逻辑
    const qs = new URLSearchParams()
    let apiUrl
    
    if (selectedApi.value === 'danbooru') {
      qs.set('limit', limit.toString())
      qs.set('tags', tags)
      qs.set('page', page.toString())
      apiUrl = `https://danbooru.donmai.us/posts.json?${qs.toString()}`
    } else {
      // Gelbooru API
      qs.set('page', 'dapi')
      qs.set('s', 'post')
      qs.set('q', 'index')
      qs.set('json', '1')
      qs.set('limit', limit.toString())
      qs.set('pid', (page - 1).toString())
      qs.set('tags', tags)
      apiUrl = `/api/gelbooru/posts?${qs.toString()}`
    }

    const res = await fetch(apiUrl)
    const data = await res.json()
    allRows = selectedApi.value === 'danbooru' ? data : data.post
  }
  
  // 处理 Gelbooru 的数据格式
  if (selectedApi.value === 'gelbooru') {
    allRows.forEach((row: any) => {
      // get file_ext from url
      row.file_ext = row.file_url.split('.').pop()
      row.large_file_url = row.sample_url || row.preview_url || row.file_url
      row.rating = row.rating === 'explicit' ? 'e' : 's'
      row.tag_string_general = row.tags
      row.tag_string_artist = ''
      row.tag_string_character = ''
      row.tag_string_copyright = ''
    })
  }
  
  posts.value = allRows

  page_map_value[tag_input.value] = page
  page_map.value = page_map_value
  
  // 保存 page_map 到服务器
  await fetch('/api/save-pagemap', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(page_map.value)
  });

  loading.value = false
  back_top()
}

async function click_post(post: any, event: MouseEvent) {
  const is_ctrl = event.ctrlKey

  let copy_tags = [
    ...(is_ctrl ? post.tag_string_artist.replace(/\(/g, '\\(').replace(/\)/g, '\\)').split(' ') : []),
    ...post.tag_string_character.replace(/\(/g, '\\(').replace(/\)/g, '\\)').split(' '),
    ...post.tag_string_copyright.replace(/\(/g, '\\(').replace(/\)/g, '\\)').split(' '),
    ...post.tag_string_general.replace(/\(/g, '\\(').replace(/\)/g, '\\)').split(' ')
  ]

  const censored_tags = ['censored', 'bar_censor', 'mosaic_censoring']
  const has_censored_tag = copy_tags.some(tag => censored_tags.indexOf(tag) != -1)
  copy_tags = copy_tags.filter(tag => censored_tags.indexOf(tag) == -1).map(tag => tag.replace(/(small_breasts|flat_chest)/, 'large_breasts'))

  if (has_censored_tag) {
    copy_tags.push('uncensored')
  }
  
  await navigator.clipboard.writeText(copy_tags.map(t => t.replace(/_/g, ' ')).join(', '))
  
  // 设置当前复制的图片ID
  copiedId.value = post.id
  // 1秒后重置，这样可以再次触发动画
  setTimeout(() => {
    copiedId.value = null
  }, 1000)
}

function on_mouse_enter (event: MouseEvent) {
  if (event.target instanceof HTMLVideoElement) {
    event.target.play()
    event.target.controls = false
  }
}

function on_mouse_leave (event: MouseEvent) {
  if (event.target instanceof HTMLVideoElement) {
    event.target.pause()
    event.target.controls = true
  }
}

function back_top () {
  window.scrollTo({
    top: 0,
    behavior: 'instant'
  })
}

function watch_save_to_localstorage (name: string, ref_obj: Ref) {
  watch(ref_obj, newValue => {
    localStorage.setItem('DAN_VIEWER_' + name, JSON.stringify(newValue))
  })
}

function load_from_localstorage (name: string, defaultValue: any) {
  return localStorage.getItem('DAN_VIEWER_' + name) || defaultValue
}

function load_from_localstorage_json (name: string, defaultValue: any) {
  return JSON.parse(localStorage.getItem('DAN_VIEWER_' + name) || '{}') || defaultValue
}

// 添加一个加载 page_map 的函数，并在组件挂载时调用
async function loadPageMap() {
  try {
    const response = await fetch('/api/load-pagemap');
    if (response.ok) {
      const data = await response.json();
      // 检查返回的数据是否为空对象或无效数据
      if (data && Object.keys(data).length > 0) {
        page_map.value = data;
      } else {
        // 如果服务器没有数据，尝试从本地存储加载
        const localData = load_from_localstorage_json('page_map', '{}');
        if (localData && Object.keys(localData).length > 0) {
          page_map.value = localData;
          // 将本地数据保存到服务器
          await fetch('/api/save-pagemap', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(localData)
          });
        } else {
          // 如果本地也没有数据，设置默认值
          page_map.value = {};
        }
      }
    }
  } catch (error) {
    console.error('加载 page_map 失败:', error);
    // 出错时从本地加载
    const localData = load_from_localstorage_json('page_map', '{}');
    page_map.value = localData;
  }
}

// 在组件挂载时加载 page_map
onMounted(loadPageMap);
</script>

<style>
/* 深色模式时的样式 */
@media (prefers-color-scheme: dark) {
  body {
    background-color: #121212; /* 深色背景 */
    color: #e0e0e0; /* 深色模式文字颜色 */
  }
}
</style>

<style scoped>

.flex {
  display: flex;
  flex-direction: row;
  gap: 10px;
  margin-bottom: 10px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(v-bind(columnWidth + 'px'), 1fr));
  gap: 16px;
  padding: 16px;
}

.image-item {
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: transform 0.3s ease;
}

.image-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

.image-item img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  aspect-ratio: 1;
}

.image-item video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  aspect-ratio: 1;
}

.blur {
  filter: blur(10px);
}

.image-item:hover .blur {
  filter: blur(0);
}

@keyframes shake {
  0% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  50% { transform: translateX(4px); }
  75% { transform: translateX(-4px); }
  100% { transform: translateX(0); }
}

.shake {
  animation: shake 0.5s ease-in-out;
}

/* 确保hover效果和shake动画可以同时工作 */
.image-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

.shake.image-item:hover {
  animation: shake 0.5s ease-in-out, translateY(-4px);
}

.image-item {
  position: relative;
}

.post-id-link {
  position: absolute;
  bottom: 8px;
  left: 8px;
  background-color: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  text-decoration: none;
  font-size: 12px;
  z-index: 1;
}

.post-id-link:hover {
  background-color: rgba(0, 0, 0, 0.8);
}

.or-search-info {
  background: linear-gradient(90deg, #4CAF50, #45a049);
  color: white;
  padding: 8px 16px;
  border-radius: 4px;
  text-align: center;
  margin-bottom: 10px;
  font-size: 14px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
</style>
