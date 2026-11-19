<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Delete, Edit, Plus, Refresh, Star } from '@element-plus/icons-vue'

import { aiApi } from '@/api/ai'
import { resolveErrorMessage } from '@/api/client'
import type {
  ModelConfig,
  ModelConfigPayload,
  ModelType,
  ProviderOption,
  UsageSummary,
} from '@/types/ai'

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const configs = ref<ModelConfig[]>([])
const providers = ref<ProviderOption[]>([])
const usage = ref<UsageSummary | null>(null)

const form = reactive({
  model_name: '',
  provider: 'bailian',
  model_type: 'llm' as ModelType,
  base_url: '',
  api_key: '',
  temperature: 0.7,
  is_default: false,
  is_enabled: true,
})

const rules: FormRules = {
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择厂商', trigger: 'change' }],
}

const typeOptions: Array<{ label: string; value: ModelType }> = [
  { label: '对话（LLM）', value: 'llm' },
  { label: '向量（Embedding）', value: 'embedding' },
  { label: '重排（Rerank）', value: 'rerank' },
]

const providerMap = computed(() => {
  const map: Record<string, ProviderOption> = {}
  for (const item of providers.value) {
    map[item.provider] = item
  }
  return map
})

const currentProvider = computed(() => providerMap.value[form.provider])
const baseUrlPlaceholder = computed(
  () => currentProvider.value?.base_url || '留空则使用厂商默认端点',
)

function providerLabel(code: string): string {
  return providerMap.value[code]?.label ?? code
}

function typeLabel(type: string): string {
  return typeOptions.find((item) => item.value === type)?.label ?? type
}

function formatNumber(value: number): string {
  return value.toLocaleString('zh-CN')
}

async function loadAll(): Promise<void> {
  loading.value = true
  try {
    const [listRes, usageRes] = await Promise.all([aiApi.listModels(), aiApi.usage(7)])
    configs.value = listRes.data
    usage.value = usageRes.data
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '加载模型配置失败'))
  } finally {
    loading.value = false
  }
}

async function loadProviders(): Promise<void> {
  try {
    const { data } = await aiApi.providers()
    providers.value = data
  } catch {
    /* 厂商列表失败不阻塞主流程 */
  }
}

function resetForm(): void {
  editingId.value = null
  form.model_name = ''
  form.provider = 'bailian'
  form.model_type = 'llm'
  form.base_url = ''
  form.api_key = ''
  form.temperature = 0.7
  form.is_default = false
  form.is_enabled = true
  formRef.value?.clearValidate()
}

function openCreate(): void {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: ModelConfig): void {
  editingId.value = row.id
  form.model_name = row.model_name
  form.provider = row.provider
  form.model_type = row.model_type
  form.base_url = row.base_url ?? ''
  form.api_key = ''
  const temperature = row.parameters?.temperature
  form.temperature = typeof temperature === 'number' ? temperature : 0.7
  form.is_default = row.is_default
  form.is_enabled = row.is_enabled
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

function onProviderChange(): void {
  if (!form.model_name && currentProvider.value) {
    form.model_name = currentProvider.value.default_model
  }
}

async function submit(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const payload: ModelConfigPayload = {
    model_name: form.model_name.trim(),
    provider: form.provider,
    model_type: form.model_type,
    base_url: form.base_url.trim() || null,
    is_default: form.is_default,
    is_enabled: form.is_enabled,
    parameters: { temperature: form.temperature },
  }
  if (form.api_key.trim()) {
    payload.api_key = form.api_key.trim()
  }

  saving.value = true
  try {
    if (editingId.value === null) {
      await aiApi.createModel(payload)
      ElMessage.success('模型配置已创建')
    } else {
      await aiApi.updateModel(editingId.value, payload)
      ElMessage.success('模型配置已更新')
    }
    dialogVisible.value = false
    await loadAll()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function remove(row: ModelConfig): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定删除模型「${row.model_name}」吗？删除后使用该配置的对话会回落到其它默认模型。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await aiApi.deleteModel(row.id)
    ElMessage.success('已删除')
    await loadAll()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '删除失败'))
  }
}

async function toggleDefault(row: ModelConfig): Promise<void> {
  try {
    await aiApi.updateModel(row.id, { is_default: true })
    ElMessage.success(`已将「${row.model_name}」设为默认`)
    await loadAll()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '设置失败'))
  }
}

onMounted(async () => {
  await loadProviders()
  await loadAll()
})
</script>

<template>
  <div class="model-page">
    <el-row :gutter="16" class="stat-row">
      <el-col :span="8">
        <el-card shadow="never">
          <div class="stat-label">近 7 天调用</div>
          <div class="stat-value">{{ formatNumber(usage?.calls ?? 0) }} <span>次</span></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <div class="stat-label">输入 tokens</div>
          <div class="stat-value">{{ formatNumber(usage?.input_tokens ?? 0) }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <div class="stat-label">输出 tokens</div>
          <div class="stat-value">{{ formatNumber(usage?.output_tokens ?? 0) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <span class="card-title">AI 模型配置</span>
            <el-tag size="small" effect="plain" type="info" class="ml-8">
              Key 加密存储，接口只回显掩码
            </el-tag>
          </div>
          <div class="card-actions">
            <el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新</el-button>
            <el-button type="primary" :icon="Plus" @click="openCreate">新增模型</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="configs" border stripe>
        <el-table-column prop="model_name" label="模型名称" min-width="170">
          <template #default="{ row }">
            <span class="model-name">{{ row.model_name }}</span>
            <el-tag v-if="row.is_default" size="small" type="success" class="ml-8">默认</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="厂商" min-width="120">
          <template #default="{ row }">{{ providerLabel(row.provider) }}</template>
        </el-table-column>
        <el-table-column label="类型" width="150">
          <template #default="{ row }">{{ typeLabel(row.model_type) }}</template>
        </el-table-column>
        <el-table-column label="API Key" min-width="150">
          <template #default="{ row }">
            <span v-if="row.has_api_key" class="mono">{{ row.api_key_masked }}</span>
            <span v-else class="muted">未配置</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small" effect="plain">
              {{ row.is_enabled ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="!row.is_default"
              :icon="Star"
              text
              type="primary"
              @click="toggleDefault(row)"
            >
              设为默认
            </el-button>
            <el-button :icon="Edit" text @click="openEdit(row)">编辑</el-button>
            <el-button :icon="Delete" text type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="还没有模型配置，点右上角「新增模型」开始" />
        </template>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId === null ? '新增模型配置' : '编辑模型配置'"
      width="560px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="模型名称" prop="model_name">
          <el-input v-model="form.model_name" placeholder="例如 qwen-plus" clearable />
        </el-form-item>

        <el-form-item label="厂商" prop="provider">
          <el-select v-model="form.provider" class="full" @change="onProviderChange">
            <el-option
              v-for="item in providers"
              :key="item.provider"
              :label="item.label"
              :value="item.provider"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="类型" prop="model_type">
          <el-select v-model="form.model_type" class="full">
            <el-option
              v-for="item in typeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Base URL">
          <el-input v-model="form.base_url" :placeholder="baseUrlPlaceholder" clearable />
        </el-form-item>

        <el-form-item label="API Key">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            :placeholder="
              editingId === null ? '粘贴厂商控制台的 Key' : '留空表示不修改现有 Key'
            "
          />
        </el-form-item>

        <el-form-item label="温度">
          <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input />
        </el-form-item>

        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
          <span class="form-hint">同类型下只能有一个默认模型</span>
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stat-row {
  margin-bottom: 16px;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

.stat-value {
  margin-top: 6px;
  font-size: 22px;
  font-weight: 600;
  color: #303133;
}

.stat-value span {
  font-size: 13px;
  font-weight: 400;
  color: #909399;
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

.card-actions {
  display: flex;
  gap: 8px;
}

.model-name {
  font-weight: 500;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  color: #606266;
}

.muted {
  color: #c0c4cc;
}

.ml-8 {
  margin-left: 8px;
}

.full {
  width: 100%;
}

.form-hint {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}
</style>
