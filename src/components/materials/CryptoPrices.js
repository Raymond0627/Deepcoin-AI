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
  const [predictedData, setPredictedData] = useState([]);
  const [loadingPrediction, setLoadingPrediction] = useState(false);
  const [predictedPrice, setPredictedPrice] = useState(null);
  const [selectedCoin, setSelectedCoin] = useState(""); // Full name (e.g., Bitcoin)
  const [selectedCoinSymbol, setSelectedCoinSymbol] = useState(""); // Short symbol (e.g., BTC)

  const API_KEY =
    "eb87f295a75b763038e0c1583274e3279af5570b41b6a932a4fa5e24e9bded05";

  const renderLogo = (imageUrl, altText, size = "1em") => (
    <img
      src={`https://www.cryptocompare.com${imageUrl}`}
      alt={altText}
      style={{ width: size, height: size }}
    />
  );

  // Fetch crypto data for coin names and prices
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
          // By default, select the first coin
          fetchHistoricalData(
            data.Data[0].CoinInfo.Name,
            data.Data[0].CoinInfo.FullName
          );
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
    setLoading(true);
    setPredictedData([]); // Clear previous predictions
    setPredictedPrice(null);

    try {
      console.log(
        `🔄 Fetching historical data for ${coinSymbol} (${coinFullName})...`
      );

      const dbHistoryResponse = await fetch(
        `http://127.0.0.1:8000/fetch-historical-data?symbol=${coinSymbol}`
      );

      if (!dbHistoryResponse.ok) {
        throw new Error(
          `Failed to fetch historical data: ${dbHistoryResponse.statusText}`
        );
      }

      const dbHistoryData = await dbHistoryResponse.json();

      if (dbHistoryData.error) {
        console.error(
          "❌ Error fetching historical data:",
          dbHistoryData.error
        );
        setLoading(false);
        return;
      }

      const formattedHistory = dbHistoryData.map((item) => ({
        date: new Date(item.timestamp).getTime(),
        price: item.price,
      }));

      setHistoricalData(formattedHistory);
      setSelectedCoin(coinFullName); // Store full name (e.g., Bitcoin)
      setSelectedCoinSymbol(coinSymbol); // Store short symbol (e.g., BTC)

      console.log(`✅ Historical data loaded for ${coinSymbol}`);
    } catch (error) {
      console.error("❌ Error fetching historical data:", error);
    }
    setLoading(false);
  };
  
  // Function to trigger prediction
  const fetchPrediction = async () => {
    setLoadingPrediction(true);
    setPredictedPrice(null);

    try {
      console.log(`📡 Fetching prediction for ${selectedCoinSymbol}...`);

      const response = await fetch(
        `http://127.0.0.1:8000/predict?symbol=${selectedCoinSymbol}`
      );

      if (!response.ok) {
        throw new Error(`Prediction failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log("✅ Prediction received:", data);

      if (data.predictions && data.predictions.length > 0) {
        const today = new Date();
        const formattedPredictions = data.predictions.map((price, index) => ({
          date: today.getTime() + index * 86400000, // Add 1 day per prediction
          price,
          type: "Prediction",
        }));

        setPredictedData(formattedPredictions);
        setPredictedPrice(
          formattedPredictions[formattedPredictions.length - 1].price
        );
      } else {
        console.error("❌ No valid predictions found.");
      }
    } catch (error) {
      console.error("❌ Error fetching prediction:", error);
    }

    setLoadingPrediction(false);
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
        {/* Left Panel: List of Coins */}
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
                          coin.CoinInfo.Name, // short symbol, e.g., "ETH"
                          coin.CoinInfo.FullName // full name, e.g., "Ethereum"
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

        {/* Right Panel: Graph & Predict Button */}
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

          {/* Modern Predict Button */}
          <div style={{ textAlign: "center", marginTop: "20px" }}>
            <button
              onClick={fetchPrediction}
              style={{
                padding: "10px 20px",
                fontSize: "16px",
                fontWeight: "bold",
                color: "white",
                backgroundColor: "#007bff",
                border: "none",
                borderRadius: "5px",
                cursor: "pointer",
                transition: "background 0.3s",
              }}
              disabled={loadingPrediction}
            >
              {loadingPrediction ? "Predicting..." : "Predict 30-Day Price"}
            </button>
            {loadingPrediction && (
              <div style={{ marginTop: "10px", color: "white" }}>
                <span className="loader"></span> Fetching prediction...
              </div>
            )}
            {predictedPrice !== null && (
              <div
                style={{
                  marginTop: "10px",
                  fontSize: "18px",
                  fontWeight: "bold",
                  color: "lightgreen",
                }}
              >
                Predicted Price: ${predictedPrice.toFixed(2)}
              </div>
            )}
          </div>

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
                {/* Render historical data */}
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
                {/* Render predicted data */}
                {predictedData && predictedData.length > 0 && (
                  <Line
                    type="monotone"
                    data={predictedData}
                    dataKey="price"
                    stroke="green"
                    dot={false}
                    strokeWidth={2}
                    name="Predicted Price"
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CryptoDashboard;
