import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'

export default [
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node
      }
    },
    rules: {
      // Vue 3 支持 v-model 带参数（如 v-model:current-page），关闭 Vue 2 误报规则
      'vue/no-v-model-argument': 'off',
      // <script setup> 中变量在模板使用，关闭未使用变量检查
      'no-unused-vars': 'off',
      'vue/no-unused-vars': 'off',
      // 允许单词组件名
      'vue/multi-word-component-names': 'off',
      // 关闭过于严格的 HTML 格式化规则，避免大量 warning 干扰
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/attributes-order': 'off',
      'vue/html-indent': 'off',
      'vue/html-closing-bracket-newline': 'off',
      'vue/html-closing-bracket-spacing': 'off',
      'vue/first-attribute-linebreak': 'off',
      'vue/component-tags-order': 'off',
      // MarkdownPreview 用 v-html 渲染已消毒的 HTML
      'vue/no-v-html': 'off',
      // 允许单引号属性
      'vue/html-quotes': 'off'
    }
  }
]
