import React, { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload; // Get full data object
    const timestamp = new Date(data.date); // Convert raw timestamp to Date object

    // Ensure valid date
    if (isNaN(timestamp)) return null;

    const formattedDate = timestamp.toLocaleDateString();

    return (
      <div
        style={{
          backgroundColor: "rgba(0, 0, 0, 0.8)",
          padding: "5px",
          borderRadius: "3px",
          color: "white",
          border: "1px solid white",
          fontSize: "0.8em",
        }}
      >
        <p>{`Date: ${formattedDate}`}</p>
        <p>{`Price: $${data.price}`}</p>
      </div>
    );
  }
  return null;
};

const CryptoDashboard = () => {
  const [cryptoData, setCryptoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [historicalData, setHistoricalData] = useState([]);
  const [selectedCoin, setSelectedCoin] = useState("");
  const [predictedData, setPredictedData] = useState([]);

  const API_KEY =
    "eb87f295a75b763038e0c1583274e3279af5570b41b6a932a4fa5e24e9bded05";

  const renderLogo = (imageUrl, altText, size = "1em") => (
    <img
      src={`https://www.cryptocompare.com${imageUrl}`}
      alt={altText}
      style={{ width: size, height: size }}
    />
  );

  // ✅ crypto data
  useEffect(() => {
    const fetchCryptoData = async () => {
      try {
        const baseUrl =
          "https://min-api.cryptocompare.com/data/top/totalvolfull";
        const params = {
          limit: "50",
          tsym: "USD",
          sign: false,
          ascending: true,
          api_key: API_KEY,
        };
        const url = new URL(baseUrl);
        url.search = new URLSearchParams(params).toString();

        const options = {
          method: "GET",
          headers: { "Content-type": "application/json; charset=UTF-8" },
        };
        const response = await fetch(url, options);
        const data = await response.json();

        if (data.Message === "Success") {
          setCryptoData(data.Data);
          fetchHistoricalData(data.Data[0].CoinInfo.Name);
          setSelectedCoin(data.Data[0].CoinInfo.FullName);
        } else {
          console.error("Error fetching crypto data:", data.Message);
        }
        setLoading(false);
      } catch (error) {
        console.error("Error fetching crypto data:", error);
        setLoading(false);
      }
    };

    fetchCryptoData();
  }, []);

  const fetchHistoricalData = async (coinSymbol, coinFullName) => {
    try {
      // ✅ Fetch historical data
      const historyUrl = `https://min-api.cryptocompare.com/data/v2/histoday?fsym=${coinSymbol}&tsym=USD&limit=30&api_key=${API_KEY}`;
      const historyResponse = await fetch(historyUrl);
      const historyData = await historyResponse.json();

      if (historyData.Response === "Success") {
        const formattedHistory = historyData.Data.Data.map((item) => ({
          date: item.time * 1000, // Convert to timestamp
          price: item.close,
        }));
        setHistoricalData(formattedHistory);
      } else {
        console.error("Error fetching historical data:", historyData.Message);
      }

      setSelectedCoin(coinFullName);
    } catch (error) {
      console.error("Error fetching historical data:", error);
    }
  };

  // ✅ fetch prediction
  const fetchPrediction = async (coinSymbol) => {
    setLoading(true); //Show loading animation

    try {
      console.log(`🚀 Training model for ${coinSymbol}...`);
      await fetch(`http://127.0.0.1:8000/train-lstm?symbol=${coinSymbol}`);

      // ✅ Wait a few seconds, then fetch prediction
      setTimeout(async () => {
        console.log(`📊 Fetching prediction for ${coinSymbol}...`);

        const predictionUrl = `http://127.0.0.1:8000/predict?symbol=${coinSymbol}`;
        const predictionResponse = await fetch(predictionUrl);
        const predictionData = await predictionResponse.json();

        if (predictionData.predictions) {
          const today = new Date();
          const formattedPredictions = predictionData.predictions.map(
            (price, index) => ({
              date: today.getTime() + index * 86400000, // Add one day in milliseconds
              price,
              type: "Prediction",
            })
          );
          setPredictedData(formattedPredictions);
        } else {
          console.error("Error fetching predictions:", predictionData.error);
        }

        setLoading(false); // ✅ Hide loading animation
      }, 10000); // ✅ Wait 10 seconds for training
    } catch (error) {
      console.error("Error training model:", error);
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "20px", color: "white" }}>
      <div
        style={{
          display: "flex",
          gap: "10px",
          justifyContent: "space-between",
        }}
      >
        <div
          style={{
            flex: "2",
            padding: "20px",
            backgroundColor: "rgba(132, 132, 132, 0.54)",
            color: "white",
            borderRadius: "10px",
            boxShadow: "0 4px 8px rgba(0, 0, 0, 0.5)",
            maxWidth: "50%",
          }}
        >
          <h2 style={{ marginTop: "-15px", marginBottom: "0px" }}>
            Top Crypto Coins
          </h2>
          <div
            style={{
              overflowX: "auto",
              maxHeight: "400px",
              overflowY: "auto",
              scrollbarWidth: "thin",
              scrollbarColor: "rgba(255, 255, 255, 0.5) transparent",
            }}
          >
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                marginTop: "10px",
              }}
            >
              <thead>
                <tr>
                  <th style={{ textAlign: "left" }}>Coin</th>
                  <th style={{ textAlign: "left" }}>Price</th>
                  <th style={{ textAlign: "left" }}>Market Cap</th>
                  <th style={{ textAlign: "left" }}>24h Change</th>
                  <th style={{ textAlign: "left" }}>24h Volume</th>
                </tr>
              </thead>
              <tbody>
                {cryptoData && cryptoData.length > 0 ? (
                  cryptoData.map((coin, index) => (
                    <tr
                      key={index}
                      style={{
                        borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
                        cursor: "pointer",
                      }}
                      onClick={() =>
                        fetchHistoricalData(
                          coin.CoinInfo.Name,
                          coin.CoinInfo.FullName
                        )
                      }
                    >
                      <td
                        style={{
                          padding: "10px 0",
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                        }}
                      >
                        {renderLogo(
                          coin.CoinInfo.ImageUrl,
                          coin.CoinInfo.FullName,
                          "1.5em"
                        )}{" "}
                        {coin.CoinInfo.FullName} ({coin.CoinInfo.Name})
                      </td>
                      <td>{coin.DISPLAY?.USD?.PRICE || "N/A"}</td>
                      <td>{coin.DISPLAY?.USD?.MKTCAP || "N/A"}</td>
                      <td>{coin.DISPLAY?.USD?.CHANGE24HOUR || "N/A"}</td>
                      <td>{coin.DISPLAY?.USD?.VOLUME24HOURTO || "N/A"}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td
                      colSpan="5"
                      style={{ textAlign: "center", color: "gray" }}
                    >
                      No data available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div
          style={{
            flex: "1",
            padding: "20px",
            backgroundColor: "rgba(91, 91, 91, 0.7)",
            color: "white",
            borderRadius: "10px",
            boxShadow: "0 4px 8px rgba(0, 0, 0, 0.5)",
          }}
        >
          <h3 style={{ textAlign: "left", marginTop: "-10px" }}>
            Graph: {selectedCoin}
          </h3>

          <div style={{ height: "300px", marginTop: "20px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "white" }}
                  tickFormatter={(timestamp) =>
                    new Date(timestamp).toLocaleDateString()
                  }
                  label={{
                    value: "Date",
                    position: "insideBottom",
                    fill: "white",
                  }}
                />
                <YAxis
                  tick={{ fill: "white" }}
                  label={{
                    value: "Price",
                    angle: -90,
                    position: "insideLeft",
                    fill: "white",
                  }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend />

                {/* ✅ Only render if historicalData is available */}
                {historicalData && historicalData.length > 0 && (
                  <Line
                    type="monotone"
                    data={historicalData}
                    dataKey="price"
                    stroke="#8884d8"
                    dot={false}
                    strokeWidth={2}
                    name="Actual Price"
                  />
                )}

                {/* ✅ Only render if predictedData is available */}
                {predictedData && predictedData.length > 0 && (
                  <Line
                    type="monotone"
                    data={predictedData}
                    dataKey="price"
                    stroke="red"
                    dot={{ stroke: "red", strokeWidth: 2 }}
                    strokeDasharray="5 5"
                    strokeWidth={2}
                    name="Predicted Price"
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <button
            style={{
              marginTop: "20px",
              padding: "10px 20px",
              backgroundColor: "#007bff",
              color: "white",
              border: "none",
              borderRadius: "5px",
              cursor: "pointer",
            }}
            onClick={() => fetchPrediction(selectedCoin)} // ✅ Triggers prediction workflow
          >
            Predict
          </button>

          {/* ✅ Show loading animation */}
          {loading && (
            <p style={{ color: "yellow", fontWeight: "bold" }}>
              Training model... Please wait ⏳
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default CryptoDashboard;
