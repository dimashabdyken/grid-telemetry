<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { EffectScatterChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import VueECharts from 'vue-echarts'
import type { CarDataRecord } from '~/lib/types'

use([EffectScatterChart, LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{
  data: CarDataRecord | null
}>()

const chartData = ref<number[]>([])
const reduceMotion = ref(false)

if (typeof window !== 'undefined') {
  reduceMotion.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

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

const highlightPoint = computed(() => {
  const windowSize = 14
  if (chartData.value.length < 6) {
    return null
  }

  const sliceStart = Math.max(chartData.value.length - windowSize, 0)
  const windowSlice = chartData.value.slice(sliceStart)
  const maxValue = Math.max(...windowSlice)
  const maxIndex = windowSlice.lastIndexOf(maxValue)

  return {
    index: sliceStart + maxIndex,
    value: maxValue
  }
})

const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'line',
      lineStyle: { color: '#ff0000', width: 1, type: 'dashed' }
    },
    backgroundColor: '#0f0f13',
    borderColor: '#333',
    textStyle: { color: '#fff', fontFamily: 'monospace', fontSize: 10 },
    padding: [4, 8],
    borderRadius: 0
  },
  grid: {
    top: 10,
    right: 10,
    bottom: 20,
    left: 40,
    containLabel: true,
    borderColor: 'transparent'
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: chartData.value.map((_, index) => index + 1),
    axisLabel: { color: '#666', fontFamily: 'monospace', fontSize: 9 },
    axisLine: { lineStyle: { color: '#333', width: 2 } },
    splitLine: { show: true, lineStyle: { color: '#222', type: 'dashed' } }
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#666', fontFamily: 'monospace', fontSize: 9 },
    axisLine: { show: true, lineStyle: { color: '#333', width: 2 } },
    splitLine: { show: true, lineStyle: { color: '#222', type: 'dashed' } }
  },
  series: [
    {
      type: 'line',
      smooth: false,
      step: 'end',
      showSymbol: false,
      lineStyle: {
        width: 2,
        color: '#00ff00' // High visibility neon green for telemetry
      },
      itemStyle: {
        color: '#00ff00'
      },
      data: chartData.value
    },
    ...(highlightPoint.value
      ? [
          {
            type: 'effectScatter',
            coordinateSystem: 'cartesian2d',
            symbolSize: 12,
            data: [[highlightPoint.value.index + 1, highlightPoint.value.value]],
            rippleEffect: reduceMotion.value
              ? undefined
              : {
                  period: 2.6,
                  scale: 2.2,
                  brushType: 'stroke'
                },
            itemStyle: {
              color: '#e10600',
              borderColor: '#e10600',
              borderWidth: 1
            }
          }
        ]
      : [])
  ]
}))
</script>

<template>
  <VueECharts class="h-full w-full" :option="chartOption" autoresize />
</template>
