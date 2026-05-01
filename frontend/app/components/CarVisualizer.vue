<template>
  <div class="bg-[#1e1e28] rounded-xl border border-white/5 shadow-lg h-[320px] relative overflow-hidden group">
    <!-- Technical background grid -->
    <div class="absolute inset-0 opacity-10" style="background-image: radial-gradient(#ffffff 1px, transparent 1px); background-size: 24px 24px;" />

    <!-- Header -->
    <h2 class="absolute top-6 left-6 text-sm text-gray-500 uppercase font-black tracking-widest z-20">RB19 AERODYNAMICS</h2>

    <!-- The Car (Absolute positioned to ignore flex constraints and be HUGE) -->
    <div class="absolute inset-0 flex items-center justify-center pointer-events-none z-10 animate-float">
      <!-- Using negative margins and scale to make the car massive -->
      <img 
        src="/rb19.png" 
        alt="RB19" 
        class="w-[120%] max-w-none md:w-[100%] h-auto object-contain drop-shadow-[0_0_20px_rgba(255,255,255,0.15)] group-hover:scale-105 transition-transform duration-700"
      />
    </div>

    <!-- Interactive Technical Markers (Z-20 to be clickable/visible) -->
    <div class="absolute top-[25%] left-[10%] z-20 bg-black/80 border border-blue-500/50 p-2 rounded backdrop-blur-md">
      <span class="text-[10px] font-black text-blue-400 uppercase tracking-wider">Aero</span>
    </div>

    <div class="absolute bottom-[20%] right-[10%] z-20 bg-black/80 border border-red-500/50 p-2 rounded backdrop-blur-md">
      <span class="text-[10px] font-black text-red-400 uppercase tracking-wider">Power</span>
    </div>

    <div class="absolute bottom-[10%] left-[20%] z-20 bg-black/80 border border-yellow-500/50 p-2 rounded backdrop-blur-md">
      <span class="text-[10px] font-black text-yellow-400 uppercase tracking-wider">Grip</span>
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
