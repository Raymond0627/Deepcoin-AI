from fastapi import FastAPI
import psycopg2
import os
import requests
import numpy as np
import pandas as pd
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
if not os.getenv("DATABASE_URL"):
    raise EnvironmentError("DATABASE_URL is not set in the environment variables.")
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

# PostgreSQL Connection
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# CryptoCompare API Key
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
CRYPTO_API_URL = "https://min-api.cryptocompare.com/data/v2/histoday"

@app.get("/")
def home():
    return {"message": "DeepCoin AI is running! 🚀"}

@app.get("/fetch-historical-data")
def fetch_historical_data(symbol: str = "BTC"):
    """Fetches & updates historical price data for a given cryptocurrency."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # ✅ Check last stored timestamp for this symbol
    cursor.execute(
        "SELECT MAX(timestamp) FROM crypto_prices WHERE symbol=%s;", (symbol,)
    )
    last_timestamp = cursor.fetchone()[0]

    # Convert to UNIX timestamp (seconds) if exists, else fetch full 30 days
    last_timestamp = int(last_timestamp.timestamp()) if last_timestamp else None

    # ✅ Fetch only missing data (if outdated)
    params = {
        "fsym": symbol,
        "tsym": "USD",
        "limit": 30 if last_timestamp is None else 1,  # If first fetch, get 30 days; otherwise, fetch last missing day
        "api_key": CRYPTOCOMPARE_API_KEY,
    }
    response = requests.get(CRYPTO_API_URL, params=params)
    data = response.json()

    if "Data" in data and "Data" in data["Data"]:
        prices = [(day["time"], day["close"]) for day in data["Data"]["Data"]]

        for timestamp, price in prices:
            # ✅ Skip inserting duplicate timestamps
            if last_timestamp and timestamp <= last_timestamp:
                continue  

            cursor.execute(
                "INSERT INTO crypto_prices (symbol, price, timestamp) VALUES (%s, %s, TO_TIMESTAMP(%s))",
                (symbol, price, timestamp),
            )

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": f"Updated {symbol} price data successfully!"}
    else:
        return {"error": f"Failed to fetch data for {symbol}"}

@app.get("/train-lstm")
def train_lstm(symbol: str = "BTC"):
    """Train an LSTM model using past 30 days of selected cryptocurrency."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT price FROM crypto_prices WHERE symbol=%s ORDER BY timestamp DESC LIMIT 30;",
        (symbol,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if len(rows) < 30:
        return {"error": f"Not enough {symbol} data to train the model (Need at least 30 days)"}

    prices = np.array([row[0] for row in rows])[::-1]  # Reverse order for time-series

    # Normalize the data
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(prices.reshape(-1, 1))

    # Prepare training data
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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM crypto_prices WHERE symbol=%s;", (symbol,))
    row_count = cursor.fetchone()[0]

    if row_count < 30:
        print(f"🔄 Not enough {symbol} data, fetching new data...")
        fetch_historical_data(symbol)  

    cursor.execute(
        "SELECT price FROM crypto_prices WHERE symbol=%s ORDER BY timestamp DESC LIMIT 30;",
        (symbol,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if len(rows) < 30:
        return {"error": f"Still not enough {symbol} data after fetching!"}

    # ✅ Train model if missing
    if not os.path.exists(model_path):
        print(f"🚀 Model for {symbol} not found, training a new one...")
        train_lstm(symbol)  

    # ✅ Load Model & Predict
    model = keras.models.load_model(model_path)
    prices = np.array([row[0] for row in rows])[::-1]  

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
