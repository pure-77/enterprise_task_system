<template>
  <div class="chart-wrapper">
    <div ref="chartRef" :style="{ width: width, height: height }"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  type: { type: String, default: 'pie', validator: (v) => ['pie','bar','line'].includes(v) },
  data: { type: Array, default: () => [] },
  options: { type: Object, default: () => ({}) },
  width: { type: String, default: '100%' },
  height: { type: String, default: '300px' }
})

const chartRef = ref(null)
let chart = null

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function themeColors() {
  return {
    primary: cssVar('--primary-color') || '#7C3AED',
    primaryLight: cssVar('--primary-light') || '#A78BFA',
    bgPrimary: cssVar('--bg-primary') || '#fff',
    border: cssVar('--border-light') || '#E4DEF2',
    textPrimary: cssVar('--text-primary') || '#1F1A37',
    textSecondary: cssVar('--text-secondary') || '#6E6A7B',
  }
}

function createChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  updateChart()
  window.addEventListener('resize', handleResize)
}

function updateChart() {
  if (!chart) return
  const t = themeColors()
  let option = {}

  if (props.type === 'pie') {
    option = {
      tooltip: {
        trigger: 'item', formatter: '{b}: {c} ({d}%)',
        backgroundColor: t.bgPrimary, borderColor: t.border, borderWidth: 1,
        textStyle: { color: t.textPrimary }
      },
      legend: { orient: 'vertical', left: 'left', textStyle: { color: t.textSecondary, fontSize: 12 } },
      series: [{
        name: '统计', type: 'pie', radius: ['40%','65%'], center: ['55%','50%'],
        data: props.data,
        itemStyle: { borderRadius: 6, borderColor: t.bgPrimary, borderWidth: 2 },
        emphasis: { itemStyle: { shadowBlur: 12, shadowColor: 'rgba(0,0,0,0.12)' } }
      }]
    }
  } else if (props.type === 'bar') {
    option = {
      tooltip: {
        trigger: 'axis', backgroundColor: t.bgPrimary,
        borderColor: t.border, textStyle: { color: t.textPrimary }
      },
      grid: { left: '3%', right: '4%', bottom: '4%', containLabel: true },
      xAxis: {
        type: 'category', data: props.data.map(i => i.name),
        axisLine: { lineStyle: { color: t.border } },
        axisLabel: { color: t.textSecondary }
      },
      yAxis: {
        type: 'value', axisLine: { show: false },
        splitLine: { lineStyle: { color: t.border } },
        axisLabel: { color: t.textSecondary }
      },
      series: [{
        type: 'bar', data: props.data.map(i => i.value),
        itemStyle: {
          borderRadius: 6,
          color: new echarts.graphic.LinearGradient(0,0,0,1,[
            { offset: 0, color: t.primary }, { offset: 1, color: t.primaryLight }
          ])
        },
        barWidth: '40%'
      }]
    }
  } else if (props.type === 'line') {
    option = {
      tooltip: {
        trigger: 'axis', backgroundColor: t.bgPrimary,
        borderColor: t.border, textStyle: { color: t.textPrimary }
      },
      grid: { left: '3%', right: '4%', bottom: '4%', containLabel: true },
      xAxis: {
        type: 'category', boundaryGap: false,
        data: props.data.map(i => i.name),
        axisLine: { lineStyle: { color: t.border } },
        axisLabel: { color: t.textSecondary }
      },
      yAxis: {
        type: 'value', axisLine: { show: false },
        splitLine: { lineStyle: { color: t.border } },
        axisLabel: { color: t.textSecondary }
      },
      series: [{
        type: 'line', smooth: true,
        data: props.data.map(i => i.value),
        itemStyle: { color: t.primary },
        lineStyle: { width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0,0,0,1,[
            { offset: 0, color: t.primaryLight + '40' },
            { offset: 1, color: t.primaryLight + '05' }
          ])
        },
        symbol: 'circle', symbolSize: 6
      }]
    }
  }

  option = { ...option, ...props.options }
  chart.setOption(option)
}

function handleResize() { chart && chart.resize() }

onMounted(() => createChart())
onUnmounted(() => { window.removeEventListener('resize', handleResize); chart && chart.dispose() })

watch(() => props.data, () => updateChart(), { deep: true })
watch(() => props.options, () => updateChart(), { deep: true })
watch([() => props.width, () => props.height], () => setTimeout(() => handleResize(), 100))
</script>

<style scoped>
.chart-wrapper { position: relative; }
</style>
