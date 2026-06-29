<template>
  <div class="profile-page">
    <el-row :gutter="16">
      <!-- 个人信息 -->
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><User /></el-icon>
              <span>个人信息</span>
            </div>
          </template>
          <el-form ref="profileRef" :model="profileForm" :rules="profileRules" label-width="80px">
            <el-form-item label="用户名">
              <el-input :value="user.username" disabled />
            </el-form-item>
            <el-form-item label="角色">
              <el-tag :type="user.role === 'admin' ? 'danger' : 'info'" size="small">
                {{ user.role === 'admin' ? '管理员' : '普通用户' }}
              </el-tag>
            </el-form-item>
            <el-form-item label="昵称" prop="nickname">
              <el-input v-model="profileForm.nickname" placeholder="显示昵称" />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="profileForm.email" placeholder="可选" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="savingProfile" @click="saveProfile">保存修改</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 修改密码 -->
      <el-col :span="10">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><Lock /></el-icon>
              <span>修改密码</span>
            </div>
          </template>
          <el-form ref="pwdRef" :model="pwdForm" :rules="pwdRules" label-width="80px">
            <el-form-item label="原密码" prop="old_password">
              <el-input v-model="pwdForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少 6 位" />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm">
              <el-input v-model="pwdForm.confirm" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="savingPwd" @click="savePassword">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { authApi } from '@/api'
import { userStore } from '@/store/user'

const user = computed(() => userStore.state.user || {})

const profileRef = ref()
const profileForm = reactive({
  nickname: '',
  email: ''
})
const profileRules = {
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }]
}
const savingProfile = ref(false)

const pwdRef = ref()
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm: ''
})
const pwdRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, val, cb) => {
        if (val !== pwdForm.new_password) cb(new Error('两次输入的密码不一致'))
        else cb()
      },
      trigger: 'blur'
    }
  ]
}
const savingPwd = ref(false)

onMounted(() => {
  profileForm.nickname = user.value.nickname || ''
  profileForm.email = user.value.email || ''
})

async function saveProfile() {
  try {
    await profileRef.value.validate()
  } catch {
    return
  }
  savingProfile.value = true
  try {
    const u = await authApi.updateMe({
      nickname: profileForm.nickname,
      email: profileForm.email
    })
    userStore.patchUser(u)
    ElMessage.success('资料已更新')
  } finally {
    savingProfile.value = false
  }
}

async function savePassword() {
  try {
    await pwdRef.value.validate()
  } catch {
    return
  }
  savingPwd.value = true
  try {
    await authApi.changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password
    })
    ElMessage.success('密码已修改，请重新登录')
    setTimeout(() => {
      userStore.logout()
      window.location.href = '/login'
    }, 1000)
  } finally {
    savingPwd.value = false
  }
}
</script>

<style scoped>
.profile-page { padding: 4px; }
.card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}
</style>
