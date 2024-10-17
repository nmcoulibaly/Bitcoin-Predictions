import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import ReactECharts from 'echarts-for-react';

const BitcoinPrediction = () => {
  const [trades, setTrades] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const ws = useRef(null);

  useEffect(() => {
    ws.current = new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@trade');

    ws.current.onopen = () => console.log("WebSocket connecté");

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const formattedTrade = {
        timestamp: data.T,
        price: parseFloat(data.p),
        volume: parseFloat(data.q),
        marketMaker: data.m
      };

      // Limiter le nombre de trades à 100 pour éviter l'entassement à l'affichage des points sur le graphe
      setTrades((limitTrades) => [formattedTrade, ...limitTrades].slice(0, 100));

      // Envoyer les données au backend Flask
      axios.post('http://localhost:5551/api/send_trade_data', formattedTrade)
        .catch(error => console.error("Erreur Axios :", error));
    };

    return () => ws.current.close();
  }, []);

  // Récupérer les prédictions depuis le backend Flask
  useEffect(() => {
    if (trades.length > 0) {
      // Les 30 dernières transactions
      const latestTrades = trades.slice(0, 30);

      axios.post('http://localhost:5551/api/get_predictions', {
        sequence: latestTrades.map(trade => [trade.price, trade.volume, trade.marketMaker])
      })
        .then(response => {
          console.log('Prédictions reçues:', response.data.prediction);
          // Remplacer complètement les prédictions pour qu'elles correspondent aux dernières transactions
          // En prenant tout le temps la dernière et donc à l'indice 0
          setPredictions(response.data.prediction[0]);
        })
        .catch(error => console.error("Erreur Axios :", error));
    }
  }, [trades]);

  const option = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: trades
        .slice(0, 30)
        .map(trade => new Date(trade.timestamp).toLocaleTimeString())
        .filter((_, index) => index % 5 === 0),
      inverse: true
    },
    yAxis: {
      type: 'value',
      min: 66800,
      max: 67400,
      interval: 50
    },
    series: [
      {
        name: 'Prix de transaction',
        type: 'line',
        data: trades.slice(0, 6).map(trade => trade.price)
      },
      {
        name: 'Prédictions',
        type: 'line',
        data: predictions.slice(0, trades.length)
      }
    ]
  };

  return (
    <div>
      <h2>Graphique en temps réel : BTC/USDT avec prédictions</h2>
      <ReactECharts option={option} />
    </div>
  );
};

export default BitcoinPrediction;
