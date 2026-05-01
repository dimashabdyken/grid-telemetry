<template>
  <div class="bg-[#1e1e28] rounded-xl border border-white/5 shadow-lg h-[320px] relative overflow-hidden group">
    <!-- Technical background grid -->
    <div class="absolute inset-0 opacity-10" style="background-image: radial-gradient(#ffffff 1px, transparent 1px); background-size: 24px 24px;" />

    <!-- Header -->
    <h2 class="absolute top-6 left-6 text-sm text-gray-500 uppercase font-black tracking-widest z-20">RB19 AERODYNAMICS</h2>

    <!-- The Car (Centered, no float, perfectly scaled) -->
    <div class="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
      <img
        src="/rb19.png"
        alt="RB19"
        class="w-[90%] md:w-[85%] h-auto max-h-[80%] object-contain drop-shadow-[0_0_20px_rgba(255,255,255,0.15)] group-hover:scale-105 transition-transform duration-700"
      />
    </div>
  </div>
</template>
