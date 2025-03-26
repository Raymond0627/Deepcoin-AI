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

# Load environment variables
load_dotenv()

app = FastAPI()

# PostgreSQL Connection
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# fetch 30 days data 

@app.get("/fetch-historical-data")
def fetch_historical_data():
    """Fetch last 30 days of BTC price data and store in PostgreSQL"""
    url = f"{CRYPTO_API_URL}?fsym=BTC&tsym=USD&limit=30&api_key={CRYPTOCOMPARE_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "Data" in data and "Data" in data["Data"]:
        prices = [(day["time"], day["close"]) for day in data["Data"]["Data"]]

        conn = get_db_connection()
        cursor = conn.cursor()

        for timestamp, price in prices:
            cursor.execute(
                "INSERT INTO crypto_prices (symbol, price, timestamp) VALUES (%s, %s, TO_TIMESTAMP(%s))",
                ("BTC", price, timestamp)
            )

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "30 days of BTC price data stored successfully!"}
    else:
        return {"error": "Failed to fetch data"}


# CryptoCompare API Key
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
CRYPTO_API_URL = "https://min-api.cryptocompare.com/data/v2/histoday"

@app.get("/train-lstm")
def train_lstm():
    """Train an LSTM model using past 30 days of BTC price data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT price FROM crypto_prices ORDER BY timestamp DESC LIMIT 30;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if len(rows) < 30:
        return {"error": "Not enough data to train the model (Need at least 30 days of data)"}

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

    # Save model
    model.save("lstm_model.h5")

    return {"message": "LSTM model trained and saved successfully!"}

@app.get("/predict")
def predict():
    """Predict next day's BTC price using trained LSTM model"""
    model = keras.models.load_model("lstm_model.h5")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT price FROM crypto_prices ORDER BY timestamp DESC LIMIT 30;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if len(rows) < 30:
        return {"error": "Not enough data for prediction"}

    prices = np.array([row[0] for row in rows])[::-1]
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(prices.reshape(-1, 1))

    last_day_price = scaled_data[-1].reshape(1, 1, 1)
    predicted_scaled = model.predict(last_day_price)
    predicted_price = scaler.inverse_transform(predicted_scaled)[0][0]

    # Convert `numpy.float32` to a standard Python `float`
    predicted_price = float(predicted_price)

    return {"predicted_price": predicted_price}
