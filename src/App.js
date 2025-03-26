import React, { useEffect, useState } from "react";
import { BrowserRouter as Router, Routes, Route, useNavigate } from "react-router-dom";
import Particles, { initParticlesEngine } from "@tsparticles/react";
import { loadFull } from "tsparticles";
import logo from "./logo.svg";
import "./App.css";
import particlesOptions from "./particles.json";
import ButtonUsage from "./components/materials/button";
import SecondPage from "./SecondPage";



// ✅ Renamed to HomePage (Fixes duplicate 'App' error)
function Homepage() {
  const [init, setInit] = useState(false);
  const navigate = useNavigate();

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
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p className="DeepcoinName">Deepcoin AI</p>
        <p className="forntDescription">
          Maximize Gains & Minimize Risk with DeepCoin AI! <br />
          Your Intelligent Assistant for Predicting Crypto Prices with Precision.
        </p>
        {/* ✅ Fixed Button Navigation */}
        <ButtonUsage onClick={() => navigate("/")} />
      </header>
    </div>
  );
}

// ✅ Router Component (Fixed Duplicate Declaration)
export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Homepage />} />
        <Route path="*" element={<SecondPage />} />
      </Routes>
    </Router>
  );
}
