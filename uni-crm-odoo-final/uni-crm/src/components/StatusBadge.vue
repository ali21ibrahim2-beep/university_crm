<!-- StatusBadge — colored pill for an OdooStatus. Three sizes. -->
<script setup lang="ts">
import type { OdooStatus } from '../types/odoo'
import { STATUS_LABELS, STATUS_COLORS } from '../types/odoo'

const props = defineProps<{ status: OdooStatus; size?: 'sm' | 'md' | 'lg' }>()
// Padding + dot sizing indexed by the `size` prop.
const sizeClasses = { sm: 'px-2 py-0.5 text-xs gap-1', md: 'px-2.5 py-1 text-xs gap-1.5', lg: 'px-3 py-1.5 text-sm gap-2' }
const dotSize = { sm: 'w-1.5 h-1.5', md: 'w-2 h-2', lg: 'w-2.5 h-2.5' }
</script>

<template>
  <span class="inline-flex items-center rounded-full font-medium"
    :class="[STATUS_COLORS[status]?.bg, STATUS_COLORS[status]?.text, sizeClasses[size || 'md']]">
    <span class="rounded-full flex-shrink-0" :class="[STATUS_COLORS[status]?.dot, dotSize[size || 'md']]" />
    {{ STATUS_LABELS[status] || status }}
  </span>
</template>
