from flask import Flask, request, jsonify
from kafka import KafkaProducer
from flask_cors import CORS
import json
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.losses import MeanSquaredError
from sklearn.preprocessing import MinMaxScaler
import pickle

app = Flask(__name__)

# Activer CORS pour toutes les routes
CORS(app)

# Configuration de Kafka Producer
producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Charger le modèle LSTM sauvegardé
model = load_model("/shared_volume_model/bitcoin_model2.h5", custom_objects={'mse': MeanSquaredError()})

# Charger le scaler utilisé lors de l'entraînement
with open("/shared_volume_model/scaler.pkl", "rb") as f:
    scaler = pickle.load(f)

# Route pour envoyer les données de trading à Kafka
@app.route('/api/send_trade_data', methods=['POST'])
def send_trade_data():
    trade_data = request.json
    producer.send('bitcoin_data_topic', trade_data)
    return jsonify({"status": "success", "message": "Trade data sent to Kafka"}), 200

# Route pour obtenir des prédictions à partir du modèle LSTM
@app.route('/api/get_predictions', methods=['POST'])
def get_predictions():
    req_data = request.json
    print(f"Données reçues pour prédiction : {req_data}")

    # Récupérer les informations (séquence de transaction ) nécessaires pour la prédiction
    seq = req_data.get('sequence')

    if seq is None or len(seq) == 0:
        return jsonify({"error": "No seq data provided"}), 400

    # Convertir la séquence reçue en un tableau numpy
    seq_array = np.array(seq)

    # Reshaper pour s'assurer que le format correspond à ce que le modèle attend (batch_size=1, seq_length, num_features)
    seq_array = seq_array.reshape((1, seq_array.shape[0], seq_array.shape[1]))

    # Normaliser la séquence en utilisant le même scaler que pour l'entraînement
    seq_array_scaled = scaler.transform(seq_array.reshape(-1, seq_array.shape[2])).reshape(seq_array.shape)

    # Faire la prédiction avec le modèle LSTM
    prediction_scaled = model.predict(seq_array_scaled)

    # Reconstruire un tableau avec 3 colonnes pour correspondre à la forme attendue par le scaler
    # On met le volume et marketMaker à 0 car nous ne prédisons que le prix
    prediction_extended = np.zeros((prediction_scaled.shape[0], prediction_scaled.shape[1], 3))
    prediction_extended[:, :, 0] = prediction_scaled  # Assigner les prédictions de prix

    # Inverser la normalisation uniquement sur la colonne du prix pour avoir les prix attendu
    prediction = scaler.inverse_transform(prediction_extended.reshape(-1, 3))[:, 0].reshape(prediction_scaled.shape)

    # Afficher la prédiction dans les logs
    print(f"PREDICTION: {prediction}")

    # Retourner la prédiction sous forme de liste
    return jsonify({"prediction": prediction.tolist()}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5550, debug=True)
