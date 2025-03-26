from fastapi import FastAPI, HTTPException
import psycopg2
import os
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

# Validate required environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
CRYPTO_API_URL = "https://min-api.cryptocompare.com/data/v2/histoday"

if not DATABASE_URL or not CRYPTOCOMPARE_API_KEY:
    raise EnvironmentError("Missing required environment variables.")

# Initialize FastAPI app
app = FastAPI()

# ✅ Enable CORS to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],  # ✅ Allows React frontend
    allow_credentials=True,
    allow_methods=["*"],  # ✅ Allows all HTTP methods
    allow_headers=["*"],  # ✅ Allows all headers
)

@app.get("/")
def home():
    return {"message": "DeepCoin AI is running! 🚀"}

def get_db_connection():
    """Create a new database connection."""
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

@app.get("/fetch-historical-data")
def fetch_historical_data(symbol: str = "BTC"):
    """Fetches & returns historical price data from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT price, timestamp FROM crypto_prices WHERE symbol=%s ORDER BY timestamp ASC;",
            (symbol,),
        )
        rows = cursor.fetchall()

        if not rows:
            return {"error": f"No historical data found for {symbol}"}

        data = [{"price": row[0], "timestamp": row[1].isoformat()} for row in rows]

        return data  # ✅ Returns correct JSON format
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        conn.close()

@app.get("/train-lstm")
def train_lstm(symbol: str = "BTC"):
    """Train an LSTM model using past 30 days of selected cryptocurrency."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT price FROM crypto_prices WHERE symbol=%s ORDER BY timestamp DESC LIMIT 30;",
            (symbol,),
        )
        rows = cursor.fetchall()

        if len(rows) < 30:
            raise HTTPException(status_code=400, detail=f"Not enough {symbol} data to train the model (Need at least 30 days)")

        prices = np.array([row[0] for row in rows])[::-1]  # Reverse order for time-series

        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(prices.reshape(-1, 1))

        X_train, y_train = [], []
        for i in range(len(scaled_data) - 1):
            X_train.append(scaled_data[i])
            y_train.append(scaled_data[i + 1])

        X_train, y_train = np.array(X_train), np.array(y_train)
        X_train = X_train.reshape((X_train.shape[0], 1, X_train.shape[1]))

        model = Sequential([
            keras.layers.Input(shape=(1, 1)),
            LSTM(50, return_sequences=True),
            LSTM(50),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mean_squared_error')

        model.fit(X_train, y_train, epochs=20, batch_size=1, verbose=0)

        model.save(f"lstm_model_{symbol}.keras")

        return {"message": f"LSTM model trained and saved successfully for {symbol}!"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        conn.close()


@app.get("/predict")
def predict(symbol: str = "BTC", days: int = 30):
    """Predict next 30 days of prices for a given cryptocurrency."""
    model_path = f"lstm_model_{symbol}.keras"

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT price FROM crypto_prices WHERE symbol=%s ORDER BY timestamp DESC LIMIT 30;",
            (symbol,),
        )
        rows = cursor.fetchall()

        if len(rows) < 30:
            raise HTTPException(status_code=400, detail=f"Not enough {symbol} data for prediction!")

        # Reverse the data to get chronological order
        prices = np.array([row[0] for row in rows])[::-1]

        # If model doesn't exist, train one
        if not os.path.exists(model_path):
            train_response = train_lstm(symbol)
            # Optionally log or handle the training response here

        model = keras.models.load_model(model_path)
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(prices.reshape(-1, 1))

        predictions = []
        # Start with the last available input
        last_input = scaled_data[-1].reshape(1, 1, 1)

        for _ in range(days):
            predicted_scaled = model.predict(last_input, verbose=0)
            predicted_price = scaler.inverse_transform(predicted_scaled)[0][0]
            predictions.append(float(predicted_price))
            # Use the prediction as the next input
            last_input = predicted_scaled.reshape(1, 1, 1)

        return {"symbol": symbol, "predictions": predictions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        conn.close()