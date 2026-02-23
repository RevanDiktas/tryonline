import * as THREE from 'three'

/**
 * Body Masking Shader for TryOn
 * 
 * This shader hides body mesh triangles that are beneath garment regions
 * to prevent poke-through artifacts without altering the actual geometry.
 * 
 * Strategy:
 * 1. Render garment to depth buffer first
 * 2. In body shader, discard fragments where garment is in front
 * 3. This creates clean masking without modifying meshes
 */

// Vertex shader for body with masking
export const bodyMaskVertexShader = `
  varying vec3 vWorldPosition;
  varying vec3 vNormal;
  varying vec2 vUv;
  
  void main() {
    vUv = uv;
    vNormal = normalize(normalMatrix * normal);
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vWorldPosition = worldPosition.xyz;
    gl_Position = projectionMatrix * viewMatrix * worldPosition;
  }
`

// Fragment shader for body with depth-based masking
export const bodyMaskFragmentShader = `
  uniform vec3 skinColor;
  uniform float roughness;
  uniform sampler2D garmentDepth;
  uniform vec2 resolution;
  uniform float maskStrength;
  
  varying vec3 vWorldPosition;
  varying vec3 vNormal;
  varying vec2 vUv;
  
  void main() {
    // Get screen coordinates for depth comparison
    vec2 screenUV = gl_FragCoord.xy / resolution;
    
    // Sample garment depth
    float garmentZ = texture2D(garmentDepth, screenUV).r;
    
    // Get current fragment depth
    float bodyZ = gl_FragCoord.z;
    
    // If garment is in front of body at this pixel, hide body
    if (garmentZ < bodyZ && garmentZ > 0.0) {
      discard;
    }
    
    // Simple skin shading
    vec3 lightDir = normalize(vec3(1.0, 1.0, 1.0));
    float diff = max(dot(vNormal, lightDir), 0.0);
    vec3 ambient = skinColor * 0.4;
    vec3 diffuse = skinColor * diff * 0.6;
    
    gl_FragColor = vec4(ambient + diffuse, 1.0);
  }
`

/**
 * Creates a body material with masking support
 */
export function createBodyMaskMaterial(skinColor: THREE.Color = new THREE.Color('#e8beac')) {
  return new THREE.ShaderMaterial({
    uniforms: {
      skinColor: { value: skinColor },
      roughness: { value: 0.7 },
      garmentDepth: { value: null },
      resolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
      maskStrength: { value: 1.0 },
    },
    vertexShader: bodyMaskVertexShader,
    fragmentShader: bodyMaskFragmentShader,
    side: THREE.FrontSide,
  })
}

/**
 * Simple approach: Hide body parts by region using vertex groups
 * This is a simpler fallback that works without custom render passes
 */
export const BODY_REGION_INDICES = {
  torso: { start: 0, end: 2000 },     // Approximate SMPL vertex ranges
  arms: { start: 2001, end: 3500 },
  legs: { start: 3501, end: 5500 },
  head: { start: 5501, end: 6890 },
}

/**
 * Hide body vertices that overlap with garment type
 */
export function getBodyMaskForGarmentType(garmentType: 'tshirt' | 'pants' | 'jacket' | 'dress') {
  switch (garmentType) {
    case 'tshirt':
      return ['torso'] // Hide torso vertices for t-shirt
    case 'pants':
      return ['legs'] // Hide leg vertices for pants
    case 'jacket':
      return ['torso', 'arms'] // Hide torso and arms for jacket
    case 'dress':
      return ['torso', 'legs'] // Hide torso and upper legs for dress
    default:
      return []
  }
}

/**
 * Apply vertex-based body masking (simpler approach)
 * Modifies mesh geometry to hide vertices in specified regions
 */
export function applyVertexMask(
  bodyMesh: THREE.Mesh,
  regionsToHide: string[],
  pushDistance: number = 0.02 // How much to push hidden vertices inward
) {
  const geometry = bodyMesh.geometry as THREE.BufferGeometry
  const positions = geometry.attributes.position
  const normals = geometry.attributes.normal
  
  if (!positions || !normals) return
  
  const posArray = positions.array as Float32Array
  const normArray = normals.array as Float32Array
  
  for (const region of regionsToHide) {
    const range = BODY_REGION_INDICES[region as keyof typeof BODY_REGION_INDICES]
    if (!range) continue
    
    // Push vertices inward along their normals
    for (let i = range.start; i <= Math.min(range.end, positions.count - 1); i++) {
      const idx = i * 3
      posArray[idx] -= normArray[idx] * pushDistance
      posArray[idx + 1] -= normArray[idx + 1] * pushDistance
      posArray[idx + 2] -= normArray[idx + 2] * pushDistance
    }
  }
  
  positions.needsUpdate = true
}

/**
 * Material that renders to depth buffer only (for garment pre-pass)
 */
export const depthOnlyMaterial = new THREE.MeshDepthMaterial({
  depthPacking: THREE.RGBADepthPacking,
})
