<!-- ProgressSteps — pipeline ribbon (new → … → enrolled).
     Shows a terminal "Lost" badge when status === 'lost'. -->
<script setup lang="ts">
import { computed } from 'vue'
import { Check } from 'lucide-vue-next'
import type { OdooStatus } from '../types/odoo'
import { STATUS_STEPS, STATUS_LABELS } from '../types/odoo'

const props = defineProps<{ currentStatus: OdooStatus }>()

// Terminal = off-pipeline; currentIndex = position on the happy path.
const isTerminal = computed(() => props.currentStatus === 'lost')
const currentIndex = computed(() => STATUS_STEPS.indexOf(props.currentStatus))
</script>

<template>
  <div class="w-full">
    <div v-if="isTerminal" class="mb-5">
      <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200">
        <span class="w-2 h-2 rounded-full bg-red-500" />
        Application Lost
      </span>
    </div>
    <div class="flex items-start justify-between w-full">
      <div v-for="(step, index) in STATUS_STEPS" :key="step" class="flex flex-col items-center flex-1 relative">
        <div v-if="index > 0" class="absolute top-4 right-1/2 left-0 h-0.5 -translate-y-1/2"
          :style="{ backgroundColor: !isTerminal && currentIndex >= index ? '#162340' : '#e5e7eb', zIndex: 0 }" />
        <div v-if="index < STATUS_STEPS.length - 1" class="absolute top-4 left-1/2 right-0 h-0.5 -translate-y-1/2"
          :style="{ backgroundColor: !isTerminal && currentIndex > index ? '#162340' : '#e5e7eb', zIndex: 0 }" />
        <div class="relative w-8 h-8 rounded-full flex items-center justify-center z-10 transition-all"
          :class="[
            !isTerminal && currentIndex > index ? 'bg-[#162340] text-white' : '',
            !isTerminal && currentIndex === index ? 'text-white ring-4 ring-[#B8966A]/25' : '',
            isTerminal || currentIndex < index ? 'bg-gray-100 text-gray-400 border-2 border-gray-200' : '',
          ]"
          :style="!isTerminal && currentIndex === index ? { backgroundColor: '#B8966A' } : undefined">
          <Check v-if="!isTerminal && currentIndex > index" class="w-4 h-4" />
          <span v-else class="text-xs font-semibold" style="font-family: Sora, sans-serif">{{ index + 1 }}</span>
        </div>
        <span class="mt-2.5 text-xs font-medium text-center leading-tight transition-colors"
          :class="[
            !isTerminal && currentIndex > index ? 'text-[#162340]' : '',
            !isTerminal && currentIndex === index ? 'text-[#B8966A]' : '',
            isTerminal || currentIndex < index ? 'text-gray-400' : '',
          ]" style="max-width: 80px">
          {{ STATUS_LABELS[step] }}
        </span>
      </div>
    </div>
  </div>
</template>
