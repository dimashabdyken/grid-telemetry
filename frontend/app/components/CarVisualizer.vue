<template>
  <div class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 shadow-lg flex items-center justify-center h-[320px] relative overflow-hidden">
    <h2 class="absolute top-6 left-6 text-sm text-gray-500 uppercase tracking-widest font-bold">RB19 AERODYNAMICS</h2>

    <!-- Floating Car Container -->
    <div class="animate-float w-full max-w-4xl px-6">
      <img
        src="/rb19.png"
        alt="RB19"
        class="max-h-[230px] w-full h-auto object-contain drop-shadow-[0_10px_20px_rgba(0,0,0,0.8)]"
      />
    </div>
  </div>
</template>

<style scoped>
@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-10px);
  }
}

.animate-float {
  animation: float 3s ease-in-out infinite;
}
</style>
