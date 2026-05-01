<template>
  <div class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 shadow-lg flex flex-col h-[320px] relative overflow-hidden">
    <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold mb-4">RB19 TECHNICAL</h2>

    <!-- Car Image Wrapper -->
    <div class="relative flex-1 flex items-center justify-center">
      <img
        src="https://www.pngall.com/wp-content/uploads/14/Red-Bull-RB19-Formula-1-Car-PNG-File.png"
        alt="Red Bull RB19"
        class="w-full h-auto object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]"
      />

      <!-- Markers -->
      <div class="absolute top-4 left-4 bg-black/60 p-2 border border-blue-500/30 rounded backdrop-blur-sm">
        <h3 class="text-[9px] font-black text-blue-500 uppercase">Aero</h3>
      </div>
      <div class="absolute bottom-4 right-4 bg-black/60 p-2 border border-red-500/30 rounded backdrop-blur-sm">
        <h3 class="text-[9px] font-black text-red-500 uppercase">Power</h3>
      </div>
    </div>
  </div>
</template>
