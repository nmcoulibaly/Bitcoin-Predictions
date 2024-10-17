#!/bin/bash

wget https://repo1.maven.org/maven2/org/mongodb/spark/mongo-spark-connector_2.13/10.2.2/mongo-spark-connector_2.13-10.2.2.jar &&
wget https://download.oracle.com/java/17/archive/jdk-17.0.8_linux-x64_bin.deb &&
pip install pymongo &&
apt-get update &&
apt-get install -y ./jdk-17.0.8_linux-x64_bin.deb
