<template>
  <div class="bg-[#1e1e28] rounded-xl p-4 border border-white/5 shadow-lg h-[320px] relative overflow-hidden flex flex-col">
    <h2 class="text-[10px] text-gray-500 uppercase font-bold tracking-widest z-10">RB19 AERODYNAMICS</h2>

    <!-- Техническая сетка на фоне -->
    <div class="absolute inset-0 opacity-[0.03]" style="background-image: radial-gradient(#ffffff 1px, transparent 1px); background-size: 20px 20px;" />

    <!-- Болид -->
    <div class="flex-1 flex items-center justify-center animate-float relative z-10">
      <img
        src="/rb19.png"
        alt="RB19"
        class="h-[180px] w-auto object-contain drop-shadow-[0_0_20px_rgba(255,255,255,0.2)] hover:scale-105 transition-transform duration-500"
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
