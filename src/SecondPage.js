import React, { useEffect, useState } from "react";
import Particles, { initParticlesEngine } from "@tsparticles/react";
import { loadFull } from "tsparticles";
import "./App.css";
import particlesOptions from "./particles.json";
import CryptoPrices from "./components/materials/CryptoPrices";


function SecondPage() {
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
    <div className="CryptoPrices">
      {init && <Particles options={particlesOptions} />}
      <CryptoPrices />
    </div>
  );
}

export default SecondPage;