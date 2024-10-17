# -*- coding: utf-8 -*-
import numpy as np
from pyspark.sql import SparkSession
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
import pickle

# Créer une session Spark pour lire les données
spark = SparkSession.builder.appName("BitcoinPriceAndPrediction").getOrCreate()

# Charger les données à partir de HDFS
df = spark.read.parquet("hdfs://namenode:9000/bitcoin_data_topic/")

# Extraire les données sous forme de tableau numpy (prix, volume, market maker)
data = df.select("price", "volume", "marketMaker").toPandas()

# Convertir la colonne "marketMaker" en 0 ou 1 (binaire), pour que le modèle puisse l'utiliser
data["marketMaker"] = data["marketMaker"].apply(lambda x: 1 if x else 0)

# Normaliser les données pour que toutes les colonnes soient sur la même échelle (entre 0 et 1)
scaler = MinMaxScaler()
data_scaled = scaler.fit_transform(data)

# Sauvegarder le scaler pour pouvoir l'utiliser dans le back pour la prédiction
with open("/shared_volume_model/scaler.pkl", "wb") as f:
    pickle.dump(scaler, f)

# Fonction pour créer des séquences de données d'entrée et les prix à prédire
def create_sequences(data, seq_length, future_steps):
  input_sequences = []
  target_prices = []

  # Boucle sur toutes les données possibles pour créer les séquences
  for i in range(len(data) - seq_length - future_steps):
      # Sélectionner une séquence d'entrée
      input_sequence = data[i:i + seq_length]

      # Sélectionner les prix futurs (on recupère que la colonne des prix, index 0)
      target_price = data[i + seq_length:i + seq_length + future_steps, 0]

      # Ajouter la séquence et le prix à prédire à la liste correspondante
      input_sequences.append(input_sequence)
      target_prices.append(target_price)

  # Convertir les listes en tableaux numpy
  input_sequences = np.array(input_sequences)
  target_prices = np.array(target_prices)

  return input_sequences, target_prices

# Définir les paramètres pour les séquences
seq_length = 30
future_steps = 6

# Créer les séquences d'entrée (X) et les prix à prédire (y)
X, y = create_sequences(data_scaled, seq_length, future_steps)

# Reshaper les données d'entrée pour les passer dans le modèle LSTM
X = X.reshape((X.shape[0], X.shape[1], X.shape[2]))

# Création du modèle LSTM
model = Sequential()

# Première couche LSTM, on spécifie la taille des séquences en entrée
model.add(LSTM(50, return_sequences=True, input_shape=(seq_length, X.shape[2])))

# Deuxième couche LSTM, sans retour des séquences (dernier état seulement)
model.add(LSTM(50))

# Couche Dense pour prédire le prix des 6 futures valeurs
model.add(Dense(future_steps))

# Compilation du modèle : on utilise 'adam' comme optimiseur et 'mse' (mean squared error) comme fonction de perte
model.compile(optimizer='adam', loss='mse', metrics=['mae'])

# Entraînement du modèle avec les données d'entrée X et les étiquettes y
model.fit(X, y, epochs=10, batch_size=32)

# Sauvegarder le modèle entraîné pour pouvoir le réutiliser plus tard
model.save("/shared_volume_model/bitcoin_model2.h5")
