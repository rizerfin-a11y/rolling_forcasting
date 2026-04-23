import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Dimensions,
  TouchableOpacity,
  Share,
} from 'react-native';
import { LineChart } from 'react-native-chart-kit';

// Colors based on Rizer scheme
const colors = {
  navy: '#1B2B6B',
  amber: '#F5A623',
  green: '#27AE60',
  red: '#E74C3C', // Using standard red for anomalous/pessimistic
  white: '#FFFFFF',
  lightGray: '#F5F6F8',
};

const API_URL = 'http://127.0.0.1:5000/api';

export default function ForecastScreen() {
  const [loading, setLoading] = useState(true);
  const [forecastData, setForecastData] = useState(null);
  const [scenarioData, setScenarioData] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [variance, setVariance] = useState(null);
  const [marketData, setMarketData] = useState(null);
  const [simpleReport, setSimpleReport] = useState('');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // 1. Fetch Forecast
      const resForecast = await fetch(`${API_URL}/forecast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metric: 'revenue', periods: 6 }),
      });
      const dataForecast = await resForecast.json();
      if (dataForecast.status === 'success') {
        setForecastData(dataForecast.data);
      }

      // 2. Fetch Scenarios
      const resScenario = await fetch(`${API_URL}/scenario`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenarios: {
            sales_growth: 10,
            cost_increase: 5,
            market_share_change: -2,
          },
        }),
      });
      const dataScenario = await resScenario.json();
      if (dataScenario.status === 'success') {
        setScenarioData(dataScenario.data);
      }

      // 3. Fetch Anomalies
      const resAnomalies = await fetch(`${API_URL}/anomalies`);
      const dataAnomalies = await resAnomalies.json();
      if (dataAnomalies.status === 'success') {
        setAnomalies(dataAnomalies.data.anomalies);
      }

      // 4. Fetch Variance
      const resVariance = await fetch(`${API_URL}/variance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          period1: 'Q3 2024',
          period2: 'Q3 2023',
          metric: 'revenue',
        }),
      });
      const dataVariance = await resVariance.json();
      if (dataVariance.status === 'success') {
        setVariance(dataVariance.data);
      }

      // 5. Fetch Market Context
      const resMarket = await fetch(`${API_URL}/market-context?company=tata-motors`);
      const dataMarket = await resMarket.json();
      if (dataMarket.status === 'success') {
        setMarketData(dataMarket.data);
      }

      // 6. Fetch Simple Report
      const resReport = await fetch(`${API_URL}/simple-report?company=tata-motors`);
      const dataReport = await resReport.json();
      if (dataReport.status === 'success') {
        setSimpleReport(dataReport.report);
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.navy} />
      </View>
    );
  }

  // Formatting chart data
  const chartLabels = [];
  const chartValues = [];
  if (forecastData) {
    // Pick last 6 historical and 6 predictions for the graph
    const hist = forecastData.historical.slice(-6);
    const pred = forecastData.predictions;

    hist.forEach((item) => {
      chartLabels.push(item.date.substring(5, 7)); // Just the month
      chartValues.push(item.value);
    });
    pred.forEach((item) => {
      chartLabels.push(item.date.substring(5, 7) + ' (P)');
      chartValues.push(item.value);
    });
  } else {
    // Fallback data
    chartLabels.push('Jan', 'Feb', 'Mar');
    chartValues.push(0, 0, 0);
  }

  const shareReport = async () => {
    try {
      await Share.share({
        message: simpleReport,
      });
    } catch (error) {
      console.error('Error sharing report:', error);
    }
  };

  const screenWidth = Dimensions.get('window').width;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.headerTitle}>Financial Forecast Engine</Text>

      {/* 1. REVENUE FORECASTING LINE CHART */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Revenue Predictor</Text>
        <Text style={styles.growthText}>
          Predicted Growth:{' '}
          <Text style={{ color: forecastData?.growth_rate_pct >= 0 ? colors.green : colors.red }}>
            {forecastData?.growth_rate_pct}%
          </Text>
        </Text>
        <LineChart
          data={{
            labels: chartLabels,
            datasets: [
              {
                data: chartValues,
              },
            ],
          }}
          width={screenWidth - 40} // from react-native
          height={220}
          yAxisLabel="₹"
          yAxisSuffix="k"
          chartConfig={{
            backgroundColor: colors.white,
            backgroundGradientFrom: colors.white,
            backgroundGradientTo: colors.white,
            decimalPlaces: 0,
            color: (opacity = 1) => `rgba(27, 43, 107, ${opacity})`,
            labelColor: (opacity = 1) => `rgba(0, 0, 0, ${opacity})`,
            style: {
              borderRadius: 16,
            },
            propsForDots: {
              r: '4',
              strokeWidth: '2',
              stroke: colors.amber,
            },
          }}
          bezier
          style={{
            marginVertical: 8,
            borderRadius: 16,
          }}
        />
      </View>

      {/* FEATURE 2: STOCK MARKET CONTEXT */}
      {marketData && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Market Sentiment Context</Text>
          <View style={styles.stockRow}>
            <View>
              <Text style={styles.stockSymbol}>TATAMOTORS.NS</Text>
              <Text style={styles.stockPrice}>₹{marketData.price}</Text>
              <Text style={[styles.stockChange, { color: marketData.change_percent >= 0 ? colors.green : colors.red }]}>
                {marketData.change_percent >= 0 ? '+' : ''}{marketData.change_percent}% (Past 30d)
              </Text>
            </View>
            <View style={styles.sparklineContainer}>
              <LineChart
                data={{
                  labels: [],
                  datasets: [{ data: marketData.chart_data }]
                }}
                width={150}
                height={60}
                withHorizontalLabels={false}
                withVerticalLabels={false}
                withDots={false}
                withInnerLines={false}
                withOuterLines={false}
                chartConfig={{
                  backgroundGradientFrom: colors.white,
                  backgroundGradientTo: colors.white,
                  color: (opacity = 1) => `rgba(27, 43, 107, ${opacity})`,
                  strokeWidth: 2,
                }}
                style={{ paddingRight: 0 }}
              />
            </View>
          </View>
          <View style={styles.aiExplanationBox}>
            <Text style={styles.aiExplanationText}>📈 Market Insight: {marketData.ai_insight}</Text>
          </View>
        </View>
      )}

      {/* FEATURE 3: SIMPLIFIED FINANCIAL REPORT */}
      {simpleReport !== '' && (
        <View style={[styles.card, { backgroundColor: '#E8F5E9', borderColor: colors.green, borderWidth: 1 }]}>
          <Text style={[styles.cardTitle, { color: colors.green }]}>Simple Report (WhatsApp Style)</Text>
          <Text style={styles.reportText}>{simpleReport}</Text>
          <TouchableOpacity style={styles.shareButton} onPress={shareReport}>
            <Text style={styles.shareBtnText}>📤 Share to WhatsApp</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* 4. VARIANCE ANALYSIS */}
      {variance && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Variance Analysis</Text>
          <View style={styles.varianceRow}>
            <Text style={styles.variancePeriodText}>
              {variance.period1.label} vs {variance.period2.label}
            </Text>
            <View style={styles.varianceValueContainer}>
              <Text
                style={[
                  styles.varianceArrow,
                  { color: variance.percentage_change >= 0 ? colors.green : colors.red },
                ]}
              >
                {variance.percentage_change >= 0 ? '▲' : '▼'}
              </Text>
              <Text style={styles.variancePercentText}>
                {Math.abs(variance.percentage_change).toFixed(1)}%
              </Text>
            </View>
          </View>
          <Text style={styles.varianceDif}>
            Abs Diff: ₹{variance.absolute_difference}
          </Text>
          <View style={styles.aiExplanationBox}>
            <Text style={styles.aiExplanationText}>💡 AI: {variance.explanation}</Text>
          </View>
        </View>
      )}

      {/* 2. WHAT-IF SCENARIOS */}
      {scenarioData && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>What-If Scenario Analysis</Text>
          <View style={styles.scenarioGrid}>
            <View style={[styles.scenarioBox, { borderTopColor: colors.green, borderTopWidth: 4 }]}>
              <Text style={styles.scenarioLabel}>Optimistic</Text>
              <Text style={styles.scenarioVal}>₹{scenarioData.optimistic.revenue}</Text>
            </View>
            <View style={[styles.scenarioBox, { borderTopColor: colors.amber, borderTopWidth: 4 }]}>
              <Text style={styles.scenarioLabel}>Base</Text>
              <Text style={styles.scenarioVal}>₹{scenarioData.base.revenue}</Text>
            </View>
            <View style={[styles.scenarioBox, { borderTopColor: colors.red, borderTopWidth: 4 }]}>
              <Text style={styles.scenarioLabel}>Pessimistic</Text>
              <Text style={styles.scenarioVal}>₹{scenarioData.pessimistic.revenue}</Text>
            </View>
          </View>
        </View>
      )}

      {/* 3. ANOMALY DETECTION */}
      {anomalies && anomalies.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Anomaly Detect Alerts</Text>
          {anomalies.map((anom, idx) => (
            <View key={idx} style={styles.anomalyAlert}>
              <View style={styles.anomalyTop}>
                <Text style={styles.anomalyDate}>⚠️ {anom.date}</Text>
                <Text style={styles.anomalyDev}>
                  {anom.deviation > 0 ? '+' : ''}{anom.deviation}σ
                </Text>
              </View>
              <Text style={styles.anomalyExpl}>{anom.explanation}</Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.lightGray,
  },
  content: {
    padding: 16,
    paddingBottom: 40,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.navy,
    marginBottom: 16,
  },
  card: {
    backgroundColor: colors.white,
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    // iOS shadow
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    // Android elevation
    elevation: 2,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.navy,
    marginBottom: 8,
  },
  growthText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 12,
  },
  // Variance
  varianceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
  },
  variancePeriodText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  varianceValueContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  varianceArrow: {
    fontSize: 18,
    marginRight: 4,
  },
  variancePercentText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  varianceDif: {
    fontSize: 14,
    color: '#777',
    marginTop: 4,
  },
  aiExplanationBox: {
    marginTop: 12,
    backgroundColor: 'rgba(245, 166, 35, 0.1)',
    padding: 10,
    borderRadius: 8,
    borderLeftWidth: 3,
    borderLeftColor: colors.amber,
  },
  aiExplanationText: {
    fontSize: 14,
    color: '#333',
    fontStyle: 'italic',
  },
  // Scenarios
  scenarioGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  scenarioBox: {
    flex: 1,
    backgroundColor: '#F9FAFC',
    padding: 10,
    marginHorizontal: 4,
    borderRadius: 8,
    alignItems: 'center',
  },
  scenarioLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
    fontWeight: '500',
  },
  scenarioVal: {
    fontSize: 14,
    fontWeight: 'bold',
    color: colors.navy,
  },
  // Anomalies
  anomalyAlert: {
    backgroundColor: '#FDEDEC',
    borderWidth: 1,
    borderColor: '#F5B7B1',
    borderRadius: 8,
    padding: 12,
    marginTop: 8,
  },
  anomalyTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  anomalyDate: {
    fontSize: 14,
    fontWeight: 'bold',
    color: colors.red,
  },
  anomalyDev: {
    fontSize: 14,
    color: colors.red,
    fontWeight: 'bold',
  },
  anomalyExpl: {
    fontSize: 13,
    color: '#333',
  },
  // Stock Card
  stockRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  stockSymbol: { fontSize: 14, color: '#666', fontWeight: '500' },
  stockPrice: { fontSize: 24, fontWeight: 'bold', color: colors.navy },
  stockChange: { fontSize: 14, fontWeight: '600' },
  sparklineContainer: { width: 150, height: 60, overflow: 'hidden' },
  // Simple Report
  reportText: { fontSize: 15, color: '#333', lineHeight: 22, marginVertical: 10 },
  shareButton: { backgroundColor: colors.green, paddingVertical: 12, borderRadius: 8, alignItems: 'center', marginTop: 10 },
  shareBtnText: { color: colors.white, fontWeight: 'bold', fontSize: 16 },
});
