<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import VueECharts from 'vue-echarts'
import type { CarDataRecord } from '~/lib/types'

use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{
  data: CarDataRecord | null
}>()

const chartData = ref<number[]>([])

watch(
  () => props.data,
  (next) => {
    if (!next) {
      return
    }

    chartData.value.push(next.speed ?? 0)
    if (chartData.value.length > 50) {
      chartData.value = chartData.value.slice(-50)
    }
  },
  { deep: true }
)

const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'line',
      lineStyle: { color: '#e10600', width: 1 }
    },
    backgroundColor: 'rgba(20, 20, 30, 0.95)',
    borderColor: '#e10600',
    textStyle: { color: '#f8fafc' }
  },
  grid: {
    top: 12,
    right: 8,
    bottom: 16,
    left: 28,
    containLabel: true,
    borderColor: 'transparent'
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: chartData.value.map((_, index) => index + 1),
    axisLabel: { color: '#94a3b8', fontSize: 10 },
    axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.25)' } },
    splitLine: { show: false }
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#94a3b8', fontSize: 10 },
    axisLine: { show: false },
    splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } }
  },
  series: [
    {
      type: 'line',
      smooth: true,
      showSymbol: false,
      lineStyle: {
        width: 3,
        color: '#00ff00'
      },
      itemStyle: {
        color: '#e10600'
      },
      areaStyle: {
        color: 'rgba(0, 255, 0, 0.12)'
      },
      data: chartData.value
    }
  ]
}))
</script>

<template>
  <VueECharts class="h-64" :option="chartOption" autoresize />
</template>
