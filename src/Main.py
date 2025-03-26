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

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS to allow frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow React frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
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
    """Fetch last 30 days of price data for a given cryptocurrency and store it in PostgreSQL."""
    url = f"{CRYPTO_API_URL}?fsym={symbol}&tsym=USD&limit=30&api_key={CRYPTOCOMPARE_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "Data" in data and "Data" in data["Data"]:
        prices = [(day["time"], day["close"]) for day in data["Data"]["Data"]]

        conn = get_db_connection()
        cursor = conn.cursor()

        for timestamp, price in prices:
            cursor.execute(
                "INSERT INTO crypto_prices (symbol, price, timestamp) VALUES (%s, %s, TO_TIMESTAMP(%s))",
                (symbol, price, timestamp)
            )

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": f"30 days of {symbol} price data stored successfully!"}
    else:
        return {"error": f"Failed to fetch data for {symbol}"}

@app.get("/train-lstm")
def train_lstm(symbol: str = "BTC"):
    """Train an LSTM model using past 30 days of selected cryptocurrency."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT price FROM crypto_prices WHERE symbol=%s ORDER BY timestamp DESC LIMIT 30;", (symbol,))
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
        LSTM(50, return_sequences=True, input_shape=(1, 1)),
        LSTM(50),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')

    # Train model
    model.fit(X_train, y_train, epochs=20, batch_size=1)

    # Save model dynamically
    model.save(f"lstm_model_{symbol}.h5")

    return {"message": f"LSTM model trained and saved successfully for {symbol}!"}

@app.get("/predict")
def predict(symbol: str = "BTC", days: int = 30):
    """Predict next 30 days of prices for a given cryptocurrency. Auto-fetch & train if needed."""
    model_path = f"lstm_model_{symbol}.h5"

    # ✅ Step 1: Fetch Data if Not Enough Data Exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM crypto_prices WHERE symbol=%s;", (symbol,))
    row_count = cursor.fetchone()[0]

    if row_count < 30:
        print(f"🔄 Not enough {symbol} data, fetching new data...")
        fetch_historical_data(symbol)  # ✅ Fetch data if needed

    cursor.execute("SELECT price FROM crypto_prices WHERE symbol=%s ORDER BY timestamp DESC LIMIT 30;", (symbol,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if len(rows) < 30:
        return {"error": f"Still not enough {symbol} data after fetching!"}

    # ✅ Step 2: Train Model if It Doesn't Exist
    if not os.path.exists(model_path):
        print(f"🚀 Model for {symbol} not found, training a new one...")
        train_lstm(symbol)  # ✅ Train model automatically

    # ✅ Step 3: Load Model & Make Predictions
    model = keras.models.load_model(model_path)
    prices = np.array([row[0] for row in rows])[::-1]  # Reverse time-series order

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(prices.reshape(-1, 1))

    predictions = []
    last_input = scaled_data[-1].reshape(1, 1, 1)

    for _ in range(days):
        predicted_scaled = model.predict(last_input)
        predicted_price = scaler.inverse_transform(predicted_scaled)[0][0]
        predictions.append(float(predicted_price))  # ✅ Convert NumPy float32 to Python float

        last_input = predicted_scaled.reshape(1, 1, 1)

    return {"symbol": symbol, "predictions": predictions}
