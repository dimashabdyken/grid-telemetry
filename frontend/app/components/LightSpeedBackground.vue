<script setup lang="ts">
import { animate } from 'framer-motion/dom'
import { onBeforeUpdate, onMounted, onUnmounted } from 'vue'

type Ray = {
  id: number
  angle: number
  distance: number
  delay: number
  duration: number
  width: number
  opacity: number
}

const RAY_COUNT = 28

const rays: Ray[] = Array.from({ length: RAY_COUNT }, (_, index) => {
  const angle = (360 / RAY_COUNT) * index + ((index * 17) % 9) - 4

  return {
    id: index,
    angle,
    distance: 360 + ((index * 37) % 240),
    delay: (index % 7) * 0.16,
    duration: 1.35 + ((index * 11) % 55) / 100,
    width: 72 + ((index * 19) % 88),
    opacity: 0.3 + ((index * 13) % 35) / 100
  }
})

const rayElements: HTMLElement[] = []
const controls: Array<{ stop: () => void }> = []

const setRayElement = (element: Element | null, index: number) => {
  if (element instanceof HTMLElement) {
    rayElements[index] = element
  }
}

onBeforeUpdate(() => {
  rayElements.length = 0
})

onMounted(() => {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  rayElements.forEach((element, index) => {
    const ray = rays[index]

    if (!ray) {
      return
    }

    if (reduceMotion) {
      element.style.opacity = '0.18'
      element.style.transform = `translateX(${ray.distance * 0.45}px) scaleX(0.5)`
      return
    }

    controls.push(
      animate(
        element,
        {
          opacity: [0, ray.opacity, 0],
          transform: [
            'translateX(0px) scaleX(0.08)',
            `translateX(${ray.distance * 0.55}px) scaleX(0.55)`,
            `translateX(${ray.distance}px) scaleX(1)`
          ]
        },
        {
          duration: ray.duration,
          delay: ray.delay,
          ease: 'easeOut',
          repeat: Infinity,
          repeatDelay: 0.12
        }
      )
    )
  })
})

onUnmounted(() => {
  controls.forEach(control => control.stop())
  controls.length = 0
})
</script>

<template>
  <div
    aria-hidden="true"
    class="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-[#15151e]"
  >
    <div class="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.08),transparent_35%)]" />
    <div
      v-for="(ray, index) in rays"
      :key="ray.id"
      class="absolute left-1/2 top-1/2 origin-left"
      :style="{ transform: `rotate(${ray.angle}deg)` }"
    >
      <div
        class="h-px origin-left rounded-full bg-gradient-to-r from-white/0 via-cyan-200/70 to-white/0"
        :ref="element => setRayElement(element, index)"
        :style="{
          width: `${ray.width}px`,
          opacity: 0
        }"
      />
    </div>
  </div>
</template>
