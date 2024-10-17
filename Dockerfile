FROM python:3.8

RUN pip install pymongo seaborn matplotlib streamlit pyspark \
    && wget https://repo1.maven.org/maven2/org/mongodb/spark/mongo-spark-connector_2.13/10.2.2/mongo-spark-connector_2.13-10.2.2.jar \
    && wget https://download.oracle.com/java/17/archive/jdk-17.0.8_linux-x64_bin.deb \
    && apt-get update \
    && apt-get install -y ./jdk-17.0.8_linux-x64_bin.deb

COPY ./model /model
COPY ./keras-h5py-truncated-file-debug-master /keras-debug

EXPOSE 8501

CMD ["streamlit", "run", "/model/monitor_streamlit.py"]
