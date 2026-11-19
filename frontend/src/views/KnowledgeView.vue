<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ElMessage,
  ElMessageBox,
  type UploadRequestOptions,
  type FormInstance,
  type FormRules,
} from 'element-plus'
import {
  Delete,
  Document as DocumentIcon,
  Files,
  Plus,
  Search,
  UploadFilled,
} from '@element-plus/icons-vue'

import { knowledgeApi } from '@/api/knowledge'
import { resolveErrorMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { KBDocument, KnowledgeBase, SearchHit } from '@/types/knowledge'

const auth = useAuthStore()

const bases = ref<KnowledgeBase[]>([])
const documents = ref<KBDocument[]>([])
const selectedId = ref<number | null>(null)
const loadingBases = ref(false)
const loadingDocs = ref(false)
const uploading = ref(false)

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', description: '', visibility: 'org' })

const rules: FormRules = {
  name: [{ required: true, message: '请输入知识库名称', trigger: 'blur' }],
}

const query = ref('')
const searching = ref(false)
const hits = ref<SearchHit[]>([])

const canCreate = computed(() => auth.has('knowledge:create'))
const canDelete = computed(() => auth.has('knowledge:delete'))
const selected = computed(
  () => bases.value.find((item) => item.id === selectedId.value) ?? null,
)

function formatSize(bytes: number | null): string {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function statusTag(status: string): 'success' | 'danger' | 'warning' {
  if (status === 'ready') return 'success'
  if (status === 'failed') return 'danger'
  return 'warning'
}

function statusText(status: string): string {
  return { ready: '已就绪', failed: '失败', processing: '处理中', pending: '等待中' }[status] ?? status
}

async function loadBases(): Promise<void> {
  loadingBases.value = true
  try {
    const { data } = await knowledgeApi.listBases()
    bases.value = data
    if (data.length && !data.some((item) => item.id === selectedId.value)) {
      selectedId.value = data[0].id
      await loadDocuments()
    }
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '加载知识库失败'))
  } finally {
    loadingBases.value = false
  }
}

async function loadDocuments(): Promise<void> {
  if (!selectedId.value) {
    documents.value = []
    return
  }
  loadingDocs.value = true
  try {
    const { data } = await knowledgeApi.listDocuments(selectedId.value)
    documents.value = data
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '加载文档失败'))
  } finally {
    loadingDocs.value = false
  }
}

async function selectBase(id: number): Promise<void> {
  if (selectedId.value === id) return
  selectedId.value = id
  hits.value = []
  query.value = ''
  await loadDocuments()
}

function openCreate(): void {
  form.name = ''
  form.description = ''
  form.visibility = 'org'
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

async function submitCreate(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const { data } = await knowledgeApi.createBase({
      name: form.name.trim(),
      description: form.description.trim() || null,
      visibility: form.visibility,
    })
    ElMessage.success('知识库已创建')
    dialogVisible.value = false
    await loadBases()
    selectedId.value = data.id
    await loadDocuments()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '创建失败'))
  } finally {
    saving.value = false
  }
}

async function removeBase(): Promise<void> {
  if (!selected.value) return
  try {
    await ElMessageBox.confirm(
      `删除「${selected.value.name}」会同时删除其下 ${selected.value.document_count} 个文档和全部向量，确定吗？`,
      '删除知识库',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await knowledgeApi.deleteBase(selected.value.id)
    ElMessage.success('已删除')
    selectedId.value = null
    documents.value = []
    hits.value = []
    await loadBases()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '删除失败'))
  }
}

async function removeDocument(row: KBDocument): Promise<void> {
  if (!selectedId.value) return
  try {
    await ElMessageBox.confirm(`确定删除文档「${row.filename}」？`, '删除文档', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await knowledgeApi.deleteDocument(selectedId.value, row.id)
    ElMessage.success('已删除')
    await loadDocuments()
    await loadBases()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '删除失败'))
  }
}

async function handleUpload(options: UploadRequestOptions): Promise<void> {
  if (!selectedId.value) return
  uploading.value = true
  try {
    const { data } = await knowledgeApi.uploadDocument(selectedId.value, options.file)
    options.onSuccess(data)
    ElMessage.success(`「${data.filename}」已入库，共 ${data.chunk_count} 个切片`)
    await loadDocuments()
    await loadBases()
  } catch (error) {
    // element-plus 的 onError 期望 UploadAjaxError，这里只关心「让上传组件进入失败态」
    ;(options.onError as (err: unknown) => void)(error)
    ElMessage.error(resolveErrorMessage(error, '上传失败'))
  } finally {
    uploading.value = false
  }
}

async function runSearch(): Promise<void> {
  const text = query.value.trim()
  if (!text || !selectedId.value) return
  searching.value = true
  try {
    const { data } = await knowledgeApi.search({
      query: text,
      kb_ids: [selectedId.value],
      top_k: 5,
    })
    hits.value = data
    if (!data.length) ElMessage.info('没有命中任何片段，试试换个问法')
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '检索失败'))
  } finally {
    searching.value = false
  }
}

onMounted(loadBases)
</script>

<template>
  <el-row :gutter="16" class="kb-page">
    <el-col :span="7">
      <el-card shadow="never" class="kb-list-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">知识库</span>
            <el-button
              v-if="canCreate"
              type="primary"
              size="small"
              :icon="Plus"
              @click="openCreate"
            >
              新建
            </el-button>
          </div>
        </template>

        <div v-loading="loadingBases" class="kb-list">
          <el-empty v-if="!bases.length" description="还没有知识库" :image-size="70" />
          <div
            v-for="item in bases"
            :key="item.id"
            class="kb-item"
            :class="{ active: item.id === selectedId }"
            @click="selectBase(item.id)"
          >
            <div class="kb-item-title">{{ item.name }}</div>
            <div class="kb-item-desc">{{ item.description || '暂无描述' }}</div>
            <div class="kb-item-meta">
              <el-tag size="small" effect="plain">{{ item.document_count }} 文档</el-tag>
              <el-tag size="small" effect="plain" type="info">
                {{ item.chunk_count }} 切片
              </el-tag>
            </div>
          </div>
        </div>
      </el-card>
    </el-col>

    <el-col :span="17">
      <el-card v-if="selected" shadow="never">
        <template #header>
          <div class="card-header">
            <div>
              <span class="card-title">{{ selected.name }}</span>
              <el-tag size="small" effect="plain" class="ml-8">
                {{ selected.visibility === 'private' ? '私有' : selected.visibility === 'department' ? '部门可见' : '全企业可见' }}
              </el-tag>
            </div>
            <el-button
              v-if="canDelete"
              type="danger"
              size="small"
              text
              :icon="Delete"
              @click="removeBase"
            >
              删除知识库
            </el-button>
          </div>
        </template>

        <!-- 上传区 -->
        <el-upload
          v-if="canCreate"
          drag
          :accept="'.txt,.md,.csv,.pdf,.docx'"
          :show-file-list="false"
          :http-request="handleUpload"
          :disabled="uploading"
          class="uploader"
        >
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="upload-text">
            {{ uploading ? '正在解析并向量化…' : '把文件拖到这里，或点击选择' }}
          </div>
          <div class="upload-hint">支持 txt / md / csv / pdf / docx，单文件不超过 20 MB</div>
        </el-upload>

        <!-- 文档列表 -->
        <el-table v-loading="loadingDocs" :data="documents" border stripe class="doc-table">
          <el-table-column label="文件名" min-width="220">
            <template #default="{ row }">
              <el-icon class="doc-icon"><DocumentIcon /></el-icon>
              <span>{{ row.filename }}</span>
            </template>
          </el-table-column>
          <el-table-column label="大小" width="100">
            <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
          </el-table-column>
          <el-table-column label="切片" width="80">
            <template #default="{ row }">{{ row.chunk_count }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status)" size="small" effect="plain">
                {{ statusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="canDelete"
                text
                type="danger"
                size="small"
                :icon="Delete"
                @click="removeDocument(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="还没有文档，上传一个试试" :image-size="70" />
          </template>
        </el-table>

        <!-- 检索测试 -->
        <div class="search-panel">
          <div class="section-title">
            <el-icon><Search /></el-icon>
            <span>语义检索测试</span>
          </div>
          <div class="search-bar">
            <el-input
              v-model="query"
              placeholder="例如：出差住宿报销上限是多少？"
              clearable
              @keyup.enter="runSearch"
            />
            <el-button type="primary" :loading="searching" @click="runSearch">检索</el-button>
          </div>

          <div v-if="hits.length" class="hits">
            <div v-for="(hit, index) in hits" :key="hit.chunk_id" class="hit">
              <div class="hit-head">
                <span class="hit-index">[{{ index + 1 }}]</span>
                <el-icon><Files /></el-icon>
                <span class="hit-file">{{ hit.filename }}</span>
                <el-tag size="small" type="success" effect="plain">
                  相似度 {{ (hit.score * 100).toFixed(1) }}%
                </el-tag>
              </div>
              <div class="hit-content">{{ hit.content }}</div>
            </div>
          </div>
        </div>
      </el-card>

      <el-card v-else shadow="never" class="empty-card">
        <el-empty description="从左侧选择一个知识库，或新建一个" />
      </el-card>
    </el-col>

    <el-dialog v-model="dialogVisible" title="新建知识库" width="480px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="例如 人事制度库" maxlength="128" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="这个知识库放什么内容"
            maxlength="2000"
          />
        </el-form-item>
        <el-form-item label="可见范围">
          <el-select v-model="form.visibility" class="full">
            <el-option label="全企业可见" value="org" />
            <el-option label="部门可见" value="department" />
            <el-option label="仅自己" value="private" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>
  </el-row>
</template>

<style scoped>
.kb-page {
  height: calc(100vh - 100px);
}

.kb-list-card {
  height: 100%;
}

.kb-list {
  max-height: calc(100vh - 220px);
  overflow-y: auto;
}

.kb-item {
  padding: 10px 12px;
  margin-bottom: 8px;
  cursor: pointer;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  transition: all 0.15s;
}

.kb-item:hover {
  border-color: #c6e2ff;
  background: #f5f9ff;
}

.kb-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.kb-item-title {
  font-weight: 600;
  color: #303133;
}

.kb-item-desc {
  margin: 4px 0 8px;
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-item-meta {
  display: flex;
  gap: 6px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.ml-8 {
  margin-left: 8px;
}

.uploader {
  margin-bottom: 16px;
}

.upload-icon {
  font-size: 42px;
  color: #c0c4cc;
}

.upload-text {
  margin-top: 8px;
  color: #606266;
}

.upload-hint {
  margin-top: 4px;
  font-size: 12px;
  color: #a8abb2;
}

.doc-table {
  margin-bottom: 16px;
}

.doc-icon {
  margin-right: 6px;
  color: #909399;
  vertical-align: middle;
}

.search-panel {
  padding-top: 8px;
  border-top: 1px dashed #ebeef5;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  font-weight: 600;
  color: #303133;
}

.search-bar {
  display: flex;
  gap: 8px;
}

.hits {
  margin-top: 12px;
}

.hit {
  padding: 10px 12px;
  margin-bottom: 8px;
  background: #fafafa;
  border-left: 3px solid #409eff;
  border-radius: 4px;
}

.hit-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 13px;
  color: #606266;
}

.hit-index {
  font-weight: 600;
  color: #409eff;
}

.hit-file {
  margin-right: auto;
}

.hit-content {
  font-size: 13px;
  line-height: 1.7;
  color: #303133;
  white-space: pre-wrap;
}

.empty-card {
  height: 100%;
}

.full {
  width: 100%;
}
</style>
