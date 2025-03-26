import React, { useEffect, useState } from "react";
import Particles, { initParticlesEngine } from "@tsparticles/react";
import { loadFull } from "tsparticles";
import particlesOptions from "../particles.json";
import "../App.css";

export default function Layout({ children }) {
  const [init, setInit] = useState(false);

  useEffect(() => {
    if (init) return;

    initParticlesEngine(async (engine) => {
      await loadFull(engine);
    }).then(() => {
      setInit(true);
    });
  }, []);

  return (
    <div className="App">
      {init && <Particles options={particlesOptions} />}
      {children} {/* This will render HomePage or PredictionPage inside */}
    </div>
  );
}
