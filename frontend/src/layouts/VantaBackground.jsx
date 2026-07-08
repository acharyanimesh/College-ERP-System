import { useEffect, useRef } from "react";
import * as THREE from "three";
import WAVES from "vanta/dist/vanta.waves.min";
import GLOBE from "vanta/dist/vanta.globe.min";
import BIRDS from "vanta/dist/vanta.birds.min";

/**
 * Role-based animated background, identical to base.html:
 * admin ('1'): waves — staff ('2'): globe — student ('3'): birds.
 * Rendered as the same <div class="vanta-bg"> the CSS positions fullscreen.
 */
const VANTA_CONFIG = {
  1: (el) =>
    WAVES({
      el,
      THREE,
      mouseControls: true,
      touchControls: true,
      gyroControls: false,
      minHeight: 200.0,
      minWidth: 200.0,
      scale: 1.0,
      scaleMobile: 1.0,
      color: 0x005588,
      shininess: 30.0,
      waveHeight: 15.0,
      waveSpeed: 1.0,
      zoom: 0.95,
    }),
  2: (el) =>
    GLOBE({
      el,
      THREE,
      mouseControls: true,
      touchControls: true,
      gyroControls: false,
      minHeight: 200.0,
      minWidth: 200.0,
      scale: 1.0,
      scaleMobile: 1.0,
      color: 0x3fa9ff,
      color2: 0xffffff,
      backgroundColor: 0x12243a,
    }),
  3: (el) =>
    BIRDS({
      el,
      THREE,
      mouseControls: true,
      touchControls: true,
      gyroControls: false,
      minHeight: 200.0,
      minWidth: 200.0,
      scale: 1.0,
      scaleMobile: 1.0,
      backgroundColor: 0x12243a,
      color1: 0x3fa9ff,
      color2: 0xff6f61,
      birdSize: 1.2,
      wingSpan: 25.0,
      speedLimit: 5.0,
      separation: 30.0,
      alignment: 25.0,
      cohesion: 25.0,
      quantity: 3.0,
    }),
};

function VantaBackground({ userType }) {
  const elRef = useRef(null);

  useEffect(() => {
    const create = VANTA_CONFIG[String(userType)];
    if (!create || !elRef.current) return undefined;
    const effect = create(elRef.current);
    return () => {
      if (effect && effect.destroy) effect.destroy();
    };
  }, [userType]);

  return <div className="vanta-bg" ref={elRef}></div>;
}

export default VantaBackground;
