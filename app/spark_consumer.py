from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp
from pyspark.sql.types import StructType, StringType, FloatType

# Créer une session Spark
spark = SparkSession.builder \
    .appName("KafkaBitcoinStream") \
    .getOrCreate()

# Schéma des données Kafka (c'est la structure des données envoyées par le WebSocket de Binance)
schema = StructType() \
    .add("timestamp", StringType()) \
    .add("price", FloatType()) \
    .add("volume", FloatType()) \
    .add("marketMaker", StringType())

# Lire les données depuis Kafka
consumer = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "bitcoin_data_topic") \
    .load()

# Les données venant de Kafka sont en format binaire, donc il faut les décoder
df = consumer.selectExpr("CAST(value AS STRING)")

# Appliquer le schéma JSON aux données
parsed_df = df.select(from_json(col("value"), schema).alias("data")).select("data.*")

# Nettoyer les données (exemple : convertir le timestamp en format timestamp Spark et gérer les valeurs nulles)
cleaned_df = parsed_df.withColumn("timestamp", to_timestamp(col("timestamp") / 1000)) \
    .na.drop()

# Enregistrer les données nettoyées dans HDFS au format Parquet
save_data_on_hdfs = cleaned_df.writeStream \
    .outputMode("append") \
    .format("parquet") \
    .option("path", "hdfs://namenode:9000/bitcoin_data_topic/") \
    .option("checkpointLocation", "hdfs://namenode:9000/bitcoin_data_topic/checkpoint/") \
    .trigger(processingTime='10 seconds').start()  # Micro-batches de 10 secondes

# Attendre que le traitement se termine
save_data_on_hdfs.awaitTermination()
