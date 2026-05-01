<script setup lang="ts">
import { MotionDirective, fadeVisible } from '@vueuse/motion'

const vMotionFadeVisible = MotionDirective(fadeVisible, true)

const carImageUrl =
  'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Lewis_Hamilton-Mercedes_W11_%285%29_%28cropped%29.jpg/1280px-Lewis_Hamilton-Mercedes_W11_%285%29_%28cropped%29.jpg'

const specs = [
  {
    title: 'Intelligent Aerodynamics',
    desc: 'Precision airflow...',
    class: 'top-[16%] left-[6%] max-w-[150px]'
  },
  {
    title: 'EQ Power',
    desc: 'Instant torque...',
    class: 'top-[58%] left-[42%] max-w-[130px]'
  },
  {
    title: 'Dynamic Control',
    desc: 'Adaptive grip...',
    class: 'top-[24%] right-[7%] max-w-[140px]'
  }
]
</script>

<template>
  <div class="relative w-full h-[400px] bg-[#1e1e28] rounded-xl overflow-hidden">
    <div class="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.08),transparent_58%)]" />

    <img
      :src="carImageUrl"
      alt="Mercedes-AMG Formula 1 car"
      class="absolute inset-0 w-full h-full object-contain p-4"
    />

    <div
      v-for="item in specs"
      :key="item.title"
      v-motion-fade-visible
      class="absolute bg-black/50 p-3 border border-white/10 backdrop-blur-md rounded-lg shadow-xl"
      :class="item.class"
    >
      <h3 class="text-white font-bold text-xs uppercase">
        {{ item.title }}
      </h3>
      <p class="text-[9px] text-gray-400">
        {{ item.desc }}
      </p>
    </div>
  </div>
</template>
