import json
import os
from fastapi import FastAPI
import psycopg2
import requests
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# Load environment variables
load_dotenv()

# Ensure required environment variables are set
if not os.getenv("CRYPTOCOMPARE_API_KEY"):
    raise EnvironmentError("CRYPTOCOMPARE_API_KEY is not set in the environment variables.")

app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CryptoCompare API Key
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
CRYPTO_API_URL = "https://min-api.cryptocompare.com/data/v2/histoday"

# JSON file for storing historical data
HISTORY_FILE = "crypto_history.json"

@app.get("/")
def home():
    return {"message": "DeepCoin AI is running! 🚀"}

@app.get("/fetch-historical-data")
def fetch_historical_data(symbol: str = "BTC"):
    """Fetches & updates historical price data for a given cryptocurrency in a single JSON file."""
    
    # ✅ Step 1: Load existing data from JSON
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as file:
            try:
                history_data = json.load(file)
            except json.JSONDecodeError:
                history_data = {}
    else:
        history_data = {}

    # ✅ Step 2: Check if data exists and is up-to-date
    if symbol in history_data:
        last_date = history_data[symbol][-1]["date"]
        last_datetime = datetime.strptime(last_date, "%Y-%m-%d")
        current_datetime = datetime.utcnow()

        # ✅ Skip fetching if already up-to-date
        if last_datetime.date() == current_datetime.date():
            return {"message": f"{symbol} data is already up to date."}

    # ✅ Step 3: Fetch new historical data
    url = f"{CRYPTO_API_URL}?fsym={symbol}&tsym=USD&limit=30&api_key={CRYPTOCOMPARE_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "Data" in data and "Data" in data["Data"]:
        prices = [
            {"date": datetime.utcfromtimestamp(day["time"]).strftime("%Y-%m-%d"), "price": day["close"]}
            for day in data["Data"]["Data"]
        ]

        # ✅ Step 4: Append new data to the existing file
        history_data[symbol] = prices

        with open(HISTORY_FILE, "w") as file:
            json.dump(history_data, file, indent=4)

        return {"message": f"Updated {symbol} price data successfully!"}
    
    return {"error": f"Failed to fetch data for {symbol}"}

@app.get("/train-lstm")
def train_lstm(symbol: str = "BTC"):
    """Train an LSTM model using past 30 days of selected cryptocurrency from JSON history."""
    
    # ✅ Load historical data
    if not os.path.exists(HISTORY_FILE):
        return {"error": "No historical data available, please fetch data first."}
    
    with open(HISTORY_FILE, "r") as file:
        history_data = json.load(file)

    if symbol not in history_data or len(history_data[symbol]) < 30:
        return {"error": f"Not enough {symbol} data to train the model (Need at least 30 days)"}

    # ✅ Prepare training data
    prices = np.array([entry["price"] for entry in history_data[symbol]])[::-1]  # Reverse order

    # Normalize the data
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(prices.reshape(-1, 1))

    # Prepare training dataset
    X_train, y_train = [], []
    for i in range(len(scaled_data) - 1):
        X_train.append(scaled_data[i])
        y_train.append(scaled_data[i + 1])

    X_train, y_train = np.array(X_train), np.array(y_train)
    X_train = np.reshape(X_train, (X_train.shape[0], 1, X_train.shape[1]))

    # Build LSTM Model
    model = Sequential([
        keras.layers.Input(shape=(1, 1)),  # Use Input layer
        LSTM(50, return_sequences=True),
        LSTM(50),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')

    # Train model
    model.fit(X_train, y_train, epochs=20, batch_size=1)

    # Save model dynamically
    model.save(f"lstm_model_{symbol}.keras")

    return {"message": f"LSTM model trained and saved successfully for {symbol}!"}

@app.get("/predict")
def predict(symbol: str = "BTC", days: int = 30):
    """Predict next 30 days of prices for a given cryptocurrency."""
    model_path = f"lstm_model_{symbol}.keras"

    # ✅ Fetch data if needed
    if not os.path.exists(HISTORY_FILE):
        return {"error": "No historical data available, please fetch data first."}
    
    with open(HISTORY_FILE, "r") as file:
        history_data = json.load(file)

    if symbol not in history_data or len(history_data[symbol]) < 30:
        print(f"🔄 Not enough {symbol} data, fetching new data...")
        fetch_historical_data(symbol)

    # ✅ Train model if missing
    if not os.path.exists(model_path):
        print(f"🚀 Model for {symbol} not found, training a new one...")
        train_lstm(symbol)

    # ✅ Load Model & Predict
    model = keras.models.load_model(model_path)
    prices = np.array([entry["price"] for entry in history_data[symbol]])[::-1]  

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(prices.reshape(-1, 1))

    predictions = []
    last_input = scaled_data[-1].reshape(1, 1, 1)

    for _ in range(days):
        predicted_scaled = model.predict(last_input)
        predicted_price = scaler.inverse_transform(predicted_scaled)[0][0]
        predictions.append(float(predicted_price))  

        last_input = predicted_scaled.reshape(1, 1, 1)

    return {"symbol": symbol, "predictions": predictions}
