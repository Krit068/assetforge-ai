'use client';

import { Suspense, useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Bounds, OrbitControls, useGLTF } from '@react-three/drei';
import * as THREE from 'three';

const FIELD_SIZE = 9;
const FIELD_COUNT = FIELD_SIZE * FIELD_SIZE;

function NeuralCubeField() {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const reducedMotion = useMemo(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    [],
  );

  useFrame(({ clock, pointer }) => {
    const mesh = meshRef.current;
    if (!mesh) return;
    const time = reducedMotion ? 0.7 : clock.getElapsedTime();

    for (let row = 0; row < FIELD_SIZE; row += 1) {
      for (let column = 0; column < FIELD_SIZE; column += 1) {
        const index = row * FIELD_SIZE + column;
        const x = (column - (FIELD_SIZE - 1) / 2) * 0.78;
        const z = (row - (FIELD_SIZE - 1) / 2) * 0.78;
        const pointerDistance = Math.hypot(x - pointer.x * 3.5, z + pointer.y * 3.5);
        const wave = Math.sin(time * 1.35 - pointerDistance * 1.28) * 0.5 + 0.5;
        const height = 0.12 + wave * 0.54;

        dummy.position.set(x, -1.52 + height / 2, z);
        dummy.rotation.set(0, time * 0.08 + index * 0.012, 0);
        dummy.scale.set(1, height / 0.34, 1);
        dummy.updateMatrix();
        mesh.setMatrixAt(index, dummy.matrix);
      }
    }

    mesh.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, FIELD_COUNT]}>
      <boxGeometry args={[0.34, 0.34, 0.34]} />
      <meshStandardMaterial
        color="#153b5e"
        emissive="#087ea4"
        emissiveIntensity={0.38}
        metalness={0.72}
        roughness={0.36}
        transparent
        opacity={0.72}
      />
    </instancedMesh>
  );
}

function BronzeChest({ wireframe, materialMode }: { wireframe: boolean; materialMode: 'pbr' | 'clay' }) {
  const clay = materialMode === 'clay';
  const material = {
    color: clay ? '#7894a6' : '#8f6334',
    metalness: clay ? 0.08 : 0.72,
    roughness: clay ? 0.84 : 0.48,
    wireframe,
  };
  const darkMaterial = {
    color: clay ? '#526776' : '#263832',
    metalness: clay ? 0.08 : 0.68,
    roughness: clay ? 0.84 : 0.5,
    wireframe,
  };

  return (
    <group rotation={[0.05, -0.48, 0]} position={[0, -0.35, 0]}>
      <mesh castShadow receiveShadow>
        <boxGeometry args={[2.7, 1.25, 1.65]} />
        <meshStandardMaterial {...material} />
      </mesh>
      <mesh position={[0, 0.78, 0]} castShadow>
        <boxGeometry args={[2.76, 0.42, 1.7]} />
        <meshStandardMaterial {...material} />
      </mesh>
      <mesh position={[0, 0.36, 0.87]} castShadow>
        <boxGeometry args={[0.48, 0.72, 0.16]} />
        <meshStandardMaterial color={clay ? '#96b4c3' : '#c38b3a'} metalness={clay ? 0.08 : 0.85} roughness={clay ? 0.84 : 0.35} wireframe={wireframe} />
      </mesh>
      {[-1.12, 1.12].map((x) => (
        <group key={x}>
          <mesh position={[x, 0, 0.86]} castShadow>
            <boxGeometry args={[0.15, 1.28, 0.09]} />
            <meshStandardMaterial {...darkMaterial} />
          </mesh>
          <mesh position={[x, 0, -0.86]} castShadow>
            <boxGeometry args={[0.15, 1.28, 0.09]} />
            <meshStandardMaterial {...darkMaterial} />
          </mesh>
        </group>
      ))}
      <mesh position={[0, -1.02, 0]} receiveShadow>
        <cylinderGeometry args={[2.1, 2.1, 0.06, 64]} />
        <meshStandardMaterial color="#1a201e" roughness={0.9} transparent opacity={0.28} />
      </mesh>
    </group>
  );
}

function GeneratedAsset({ modelUrl, wireframe, materialMode }: { modelUrl: string; wireframe: boolean; materialMode: 'pbr' | 'clay' }) {
  const { scene } = useGLTF(modelUrl);
  const clonedScene = useMemo(() => scene.clone(true), [scene]);

  useEffect(() => {
    clonedScene.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) return;
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      for (const material of materials) {
        const standardMaterial = material as THREE.MeshStandardMaterial;
        if (!standardMaterial.userData.assetForgeOriginal) {
          standardMaterial.userData.assetForgeOriginal = {
            color: standardMaterial.color?.getHex(),
            metalness: standardMaterial.metalness,
            roughness: standardMaterial.roughness,
          };
        }
        const original = standardMaterial.userData.assetForgeOriginal as {
          color?: number;
          metalness?: number;
          roughness?: number;
        };
        if (materialMode === 'clay') {
          standardMaterial.color?.set('#7894a6');
          standardMaterial.metalness = 0.08;
          standardMaterial.roughness = 0.84;
        } else {
          if (typeof original.color === 'number') standardMaterial.color?.setHex(original.color);
          if (typeof original.metalness === 'number') standardMaterial.metalness = original.metalness;
          if (typeof original.roughness === 'number') standardMaterial.roughness = original.roughness;
        }
        if ('wireframe' in material) {
          standardMaterial.wireframe = wireframe;
          material.needsUpdate = true;
        }
      }
    });
  }, [clonedScene, materialMode, wireframe]);

  return <primitive object={clonedScene} />;
}

export function AssetPreview({
  wireframe,
  modelUrl,
  materialMode = 'pbr',
}: {
  wireframe: boolean;
  modelUrl?: string | null;
  materialMode?: 'pbr' | 'clay';
}) {
  return (
    <Canvas
      camera={{ position: [4.4, 3.1, 5.1], fov: 38 }}
      shadows
      dpr={[1, 1.6]}
      aria-label="Interactive 3D preview of a bronze game asset"
    >
      <color attach="background" args={['#070b14']} />
      <fog attach="fog" args={['#070b14', 8, 18]} />
      <ambientLight intensity={0.9} />
      <directionalLight
        castShadow
        position={[3.5, 5, 4]}
        intensity={3.8}
        color="#c8f5ff"
      />
      <pointLight position={[-4, 1, -2]} intensity={3.1} color="#40e0d0" />
      <pointLight position={[4, 0, -3]} intensity={2.4} color="#8b5cf6" />
      <NeuralCubeField />
      <gridHelper args={[12, 16, '#1c6d8f', '#10233c']} position={[0, -1.54, 0]} />
      <Suspense fallback={<BronzeChest wireframe={wireframe} materialMode={materialMode} />}>
        {modelUrl ? (
          <Bounds fit clip observe margin={1.25}>
            <GeneratedAsset modelUrl={modelUrl} wireframe={wireframe} materialMode={materialMode} />
          </Bounds>
        ) : (
          <BronzeChest wireframe={wireframe} materialMode={materialMode} />
        )}
      </Suspense>
      <OrbitControls
        makeDefault
        enablePan={false}
        minDistance={4}
        maxDistance={10}
        minPolarAngle={0.45}
        maxPolarAngle={1.5}
      />
    </Canvas>
  );
}
