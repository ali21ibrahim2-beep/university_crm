<!-- StatCard — KPI tile: big number, label, icon, optional delta badge. -->
<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  label: string
  value: string | number
  icon: Component
  iconBg: string
  iconColor: string
  change?: string
  changeType?: 'up' | 'down' | 'neutral'
  sublabel?: string
}>()
</script>

<template>
  <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 flex flex-col gap-4 hover:shadow-md transition-shadow">
    <div class="flex items-start justify-between">
      <div class="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0" :class="iconBg">
        <component :is="icon" class="w-5 h-5" :class="iconColor" />
      </div>
      <span v-if="change" class="text-xs font-medium px-2 py-0.5 rounded-full"
        :class="changeType === 'up' ? 'bg-green-50 text-green-700' : changeType === 'down' ? 'bg-red-50 text-red-700' : 'bg-gray-100 text-gray-600'">
        {{ changeType === 'up' ? '↑' : changeType === 'down' ? '↓' : '' }} {{ change }}
      </span>
    </div>
    <div>
      <div class="text-3xl font-semibold text-[#162340]" style="font-family: Sora, sans-serif">{{ value }}</div>
      <div class="text-sm text-gray-500 mt-1">{{ label }}</div>
      <div v-if="sublabel" class="text-xs text-gray-400 mt-0.5">{{ sublabel }}</div>
    </div>
  </div>
</template>
