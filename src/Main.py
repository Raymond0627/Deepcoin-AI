from fastapi import FastAPI, HTTPException
import psycopg2
import os
import requests
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import tensorflow as tf
print("GPU Available:", tf.config.list_physical_devices('GPU'))

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
CRYPTO_API_URL = "https://min-api.cryptocompare.com/data/v2/histoday"

if not DATABASE_URL or not CRYPTOCOMPARE_API_KEY:
    raise EnvironmentError("Missing required environment variables.")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

# Fetch historical data from CryptoCompare and store it in the database
def fetch_and_store_crypto_data(symbol):
    try:
        response = requests.get(
            f"{CRYPTO_API_URL}?fsym={symbol}&tsym=USD&limit=2000&api_key={CRYPTOCOMPARE_API_KEY}"
        )
        data = response.json()

        if data.get("Response") != "Success":
            raise HTTPException(status_code=500, detail=f"CryptoCompare API error: {data.get('Message')}")

        conn = get_db_connection()
        cursor = conn.cursor()
        for item in data["Data"]["Data"]:
            timestamp = datetime.utcfromtimestamp(item["time"])
            price = item["close"]
            cursor.execute(
                "INSERT INTO crypto_prices (symbol, price, timestamp) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;",
                (symbol, price, timestamp),
            )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching or storing data: {str(e)}")

@app.get("/fetch-historical-data")
def fetch_historical_data(symbol: str = "BTC"):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check latest stored data
        cursor.execute(
            "SELECT price, timestamp FROM crypto_prices WHERE symbol=%s ORDER BY timestamp DESC LIMIT 1;",
            (symbol,),
        )
        row = cursor.fetchone()

        if row:
            latest_timestamp = row[1]
            current_time = datetime.utcnow()

            # If data is outdated (>24 hours old), fetch new data
            if (current_time - latest_timestamp) > timedelta(days=1):
                fetch_and_store_crypto_data(symbol)
        else:
            # If no data exists, fetch from CryptoCompare
            fetch_and_store_crypto_data(symbol)

        # Fetch updated data
        cursor.execute(
            "SELECT price, timestamp FROM crypto_prices WHERE symbol=%s ORDER BY timestamp ASC;",
            (symbol,),
        )
        rows = cursor.fetchall()
        
        if not rows:
            raise HTTPException(status_code=404, detail=f"No historical data available for {symbol}")

        data = [{"price": row[0], "timestamp": row[1].isoformat()} for row in rows]
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/predict")
def predict(symbol: str = "BTC", days: int = 30):
    """Train model and predict next 30 days of prices for a given cryptocurrency."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT price FROM crypto_prices WHERE symbol=%s ORDER BY timestamp ASC;",
            (symbol,),
        )
        rows = cursor.fetchall()
        
        if not rows or len(rows) < 30:
            raise HTTPException(status_code=400, detail=f"Not enough {symbol} data for prediction!")

        prices = np.array([row[0] for row in rows], dtype=np.float32).reshape(-1, 1)
        scaler = MinMaxScaler()
        scaled_prices = scaler.fit_transform(prices)
        
        sequence_length = 10
        X, y = [], []
        for i in range(len(scaled_prices) - sequence_length):
            X.append(scaled_prices[i:i+sequence_length])
            y.append(scaled_prices[i+sequence_length])
        
        X, y = np.array(X), np.array(y)
        
        # Create and train the model
        model = Sequential([
    LSTM(48, return_sequences=False, input_shape=(sequence_length, 1)),  
    Dense(16, activation='relu'),
    Dense(1)
    ])

        model.compile(optimizer="adam", loss="mse")
        model.fit(X, y, epochs=30, batch_size=32, verbose=0)
        
        # Generate predictions
        predictions = []
        last_input = X[-1].reshape(1, sequence_length, 1)  # Use the last sequence as starting point

        for _ in range(days):
            predicted_scaled = model.predict(last_input, verbose=0)
            predicted_price = scaler.inverse_transform(predicted_scaled)[0][0]
            predictions.append(float(predicted_price))
            # Update input for next prediction
            last_input = np.append(last_input[:, 1:, :], predicted_scaled.reshape(1, 1, 1), axis=1)

        return {"symbol": symbol, "predictions": predictions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        conn.close()
