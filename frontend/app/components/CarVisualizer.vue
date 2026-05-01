<template>
  <!-- 1. Unique Gradient Background to break monotony -->
  <div class="rounded-xl border border-white/10 shadow-2xl h-[320px] relative overflow-hidden group bg-gradient-to-br from-[#0b0f19] via-[#151a28] to-[#1a1216]">

    <!-- 2. Racing Diagonal Stripes Texture -->
    <div class="absolute inset-0 opacity-20" style="background-image: repeating-linear-gradient(-45deg, transparent, transparent 4px, rgba(255,255,255,0.05) 4px, rgba(255,255,255,0.05) 8px);"></div>

    <!-- 3. Studio Lighting Glow (Vibrant Blue & Red) -->
    <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
      <div class="absolute w-[70%] h-[60%] bg-[#005aff] opacity-30 blur-[100px] rounded-full -translate-x-12"></div>
      <div class="absolute w-[50%] h-[50%] bg-[#e10600] opacity-20 blur-[80px] rounded-full translate-x-20"></div>
    </div>

    <!-- 4. Header with Red Accent -->
    <h2 class="absolute top-6 left-6 text-sm text-gray-400 uppercase tracking-widest font-bold z-20">CAR</h2>

    <!-- Red Bull Racing Logo -->
    <img
      src="/red_bull_racing_logo.png"
      alt="Red Bull Racing"
      class="absolute top-5 right-6 z-20 h-8 md:h-10 w-auto object-contain"
    />

    <!-- 5. Bold Visible Typography -->
    <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none select-none z-0">
      <span class="text-[120px] md:text-[160px] lg:text-[180px] font-black italic tracking-tighter text-white/10 drop-shadow-lg -translate-y-4">
        RB19
      </span>
      <span class="text-xs md:text-sm font-bold tracking-[1em] text-white/20 uppercase -translate-y-8">
        Oracle Red Bull Racing
      </span>
    </div>

    <!-- 6. The Car -->
    <div class="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
      <img
        src="/rb19.png"
        alt="RB19"
        class="w-[131%] md:w-[124%] h-auto max-h-[111%] object-contain drop-shadow-[0_25px_25px_rgba(0,0,0,0.9)] group-hover:scale-105 transition-transform duration-700"
      />
    </div>
  </div>
</template>
