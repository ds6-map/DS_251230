<script setup lang="ts">
import Map3DInterface from '@/components/Map3DInterface.vue'
</script>

<template>
  <div class="map3d-view">
    <Map3DInterface />
  </div>
</template>

<style scoped>
.map3d-view {
  width: 100%;
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
  background: linear-gradient(135deg, #000a0a 0%, #001414 40%, #000a12 100%);
}
</style>

