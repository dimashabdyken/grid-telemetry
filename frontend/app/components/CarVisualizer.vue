<template>
  <div class="border border-edge bg-surface h-[320px] relative overflow-hidden group">
    <h2 class="absolute top-5 left-5 text-[10px] text-gray-400 uppercase tracking-[0.2em] font-mono z-20">CAR</h2>

    <!-- Red Bull Racing Logo -->
    <img
      src="/red_bull_racing_logo.png"
      alt="Red Bull Racing"
      class="absolute top-5 right-6 z-20 h-8 md:h-10 w-auto object-contain"
    />

    <!-- 5. Bold Visible Typography -->
    <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none select-none z-0">
      <span class="text-[120px] md:text-[160px] lg:text-[180px] font-black tracking-tighter text-white/10 -translate-y-4">
        RB19
      </span>
      <span class="text-xs md:text-sm font-mono tracking-[1em] text-white/20 uppercase -translate-y-8">
        Oracle Red Bull Racing
      </span>
    </div>

    <!-- 6. The Car -->
    <div class="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
      <img
        src="/rb19.png"
        alt="RB19"
        class="w-[151%] md:w-[143%] h-auto max-h-[128%] object-contain drop-shadow-[0_18px_18px_rgba(0,0,0,0.8)]"
      />
    </div>
  </div>
</template>
