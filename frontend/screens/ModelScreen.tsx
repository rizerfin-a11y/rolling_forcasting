import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput, Modal, ActivityIndicator, Animated } from 'react-native';
import Slider from '@react-native-community/slider';
import { LineChart } from 'react-native-chart-kit';
import { Dimensions } from 'react-native';

const screenWidth = Dimensions.get('window').width;

const RIZER_COLORS = {
    Navy: '#1B2B6B',
    Indigo: '#4F5BD5',
    Amber: '#F5A623',
    Green: '#27AE60',
    Red: '#E74C3C',
    LightGray: '#F5F6FA',
    White: '#FFFFFF',
    Gray: '#95A5A6'
};

const API_BASE = 'https://rizer-backend-4kvl.onrender.com/api';

type TabName = 'Drivers' | 'Dimensions' | 'Rolling' | 'Budget' | 'Connect';

export default function ModelScreen() {
    const [activeTab, setActiveTab] = useState<TabName>('Drivers');

    return (
        <View style={styles.container}>
            <Text style={styles.headerTitle}>Engine Models</Text>

            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabScroll}>
                <View style={styles.tabContainer}>
                    {(['Drivers', 'Dimensions', 'Rolling', 'Budget', 'Connect'] as TabName[]).map(tab => (
                        <TouchableOpacity
                            key={tab}
                            style={[styles.tabButton, activeTab === tab && styles.activeTab]}
                            onPress={() => setActiveTab(tab)}
                        >
                            <Text style={[styles.tabText, activeTab === tab && styles.activeTabText]}>{tab}</Text>
                        </TouchableOpacity>
                    ))}
                </View>
            </ScrollView>

            <ScrollView contentContainerStyle={styles.content}>
                {activeTab === 'Drivers' && <DriversTab />}
                {activeTab === 'Dimensions' && <DimensionsTab />}
                {activeTab === 'Rolling' && <RollingTab />}
                {activeTab === 'Budget' && <BudgetTab />}
                {activeTab === 'Connect' && <ConnectTab />}
            </ScrollView>
        </View>
    );
}

// DRIVERS TAB — with Propagation Cascade ─────────────────────────────
function DriversTab() {
    const [drivers, setDrivers] = useState({
        sales_volume: 350000,
        average_price: 1200000,
        cost_of_goods_percent: 72,
        operating_expenses: 8000,
        tax_rate: 25,
        total_market_size: 4200000
    });

    const [metrics, setMetrics] = useState<any>(null);
    const [cascade, setCascade] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const flashAnim = useRef(new Animated.Value(0)).current;

    const [goalModal, setGoalModal] = useState(false);
    const [targetProfit, setTargetProfit] = useState('2000');
    const [goalResult, setGoalResult] = useState<any>(null);
    const [lastChanged, setLastChanged] = useState<string>('sales_volume');

    const propagate = async (currentDrivers: any, changedDriver: string) => {
        try {
            setLoading(true);
            const res = await fetch(`${API_BASE}/drivers/propagate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    driver: changedDriver,
                    new_value: currentDrivers[changedDriver],
                    current_drivers: currentDrivers
                })
            });
            const data = await res.json();
            if (data.status === 'success') {
                setMetrics(data.propagation.all_metrics);
                setCascade(data.propagation);

                // Trigger amber flash animation
                Animated.sequence([
                    Animated.timing(flashAnim, { toValue: 1, duration: 200, useNativeDriver: false }),
                    Animated.timing(flashAnim, { toValue: 0, duration: 600, useNativeDriver: false }),
                ]).start();
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const handler = setTimeout(() => {
            propagate(drivers, lastChanged);
        }, 300);
        return () => clearTimeout(handler);
    }, [drivers]);

    const runGoalSeek = async () => {
        try {
            const res = await fetch(`${API_BASE}/drivers/goal-seek`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    drivers,
                    target_metric: 'net_profit',
                    target_value: parseFloat(targetProfit),
                    variable_driver: 'sales_volume'
                })
            });
            const data = await res.json();
            if (data.status === 'success') setGoalResult(data.goal_seek);
        } catch (e) { console.error(e); }
    };

    const getCardColor = (margin: number) => {
        if (margin > 10) return RIZER_COLORS.Green;
        if (margin >= 5) return RIZER_COLORS.Amber;
        return RIZER_COLORS.Red;
    };

    const margin = metrics ? metrics.profit_margin : 0;
    const cardColor = getCardColor(margin);
    const animBg = flashAnim.interpolate({
        inputRange: [0, 1],
        outputRange: ['rgba(245,166,35,0)', 'rgba(245,166,35,0.3)']
    });

    return (
        <View style={styles.tabSection}>
            <Animated.View style={[styles.metricsContainer, { backgroundColor: animBg }]}>
                {metrics && <>
                    <View style={[styles.metricCard, { borderLeftColor: cardColor, borderLeftWidth: 4 }]}>
                        <Text style={styles.metricLabel}>Revenue</Text>
                        <Text style={styles.metricValue}>₹{metrics.revenue?.toFixed(1)}Cr</Text>
                    </View>
                    <View style={[styles.metricCard, { borderLeftColor: cardColor, borderLeftWidth: 4 }]}>
                        <Text style={styles.metricLabel}>Net Profit</Text>
                        <Text style={styles.metricValue}>₹{metrics.net_profit?.toFixed(1)}Cr</Text>
                    </View>
                    <View style={[styles.metricCard, { borderLeftColor: cardColor, borderLeftWidth: 4 }]}>
                        <Text style={styles.metricLabel}>Margin</Text>
                        <Text style={[styles.metricValue, { color: cardColor }]}>{metrics.profit_margin?.toFixed(1)}%</Text>
                    </View>
                </>}
            </Animated.View>

            {/* Cascade Effect */}
            {cascade && cascade.propagation_path && cascade.propagation_path.length > 0 && (
                <View style={styles.cascadeBox}>
                    <Text style={styles.cascadeTitle}>⚡ Cascade Effect ({cascade.cascade_count} metrics affected)</Text>
                    {cascade.propagation_path.slice(0, 5).map((path: string, i: number) => (
                        <Text key={i} style={styles.cascadePath}>{path}</Text>
                    ))}
                    {cascade.changes && cascade.changes.slice(0, 4).map((c: any, i: number) => (
                        <Text key={`c${i}`} style={[styles.cascadeChange, { color: c.change_pct >= 0 ? RIZER_COLORS.Green : RIZER_COLORS.Red }]}>
                            {c.metric}: {c.change_pct >= 0 ? '+' : ''}{c.change_pct}%
                        </Text>
                    ))}
                </View>
            )}

            <TouchableOpacity style={styles.actionBtn} onPress={() => setGoalModal(true)}>
                <Text style={styles.actionBtnText}>Goal Seek</Text>
            </TouchableOpacity>

            <View style={styles.sliderSection}>
                <Text style={styles.sliderLabel}>Sales Volume: {Math.round(drivers.sales_volume)} units</Text>
                <Slider minimumValue={0} maximumValue={500000} value={drivers.sales_volume}
                    onValueChange={(v) => { setLastChanged('sales_volume'); setDrivers({ ...drivers, sales_volume: v }); }}
                    minimumTrackTintColor={RIZER_COLORS.Indigo} />

                <Text style={styles.sliderLabel}>Avg Price: ₹{Math.round(drivers.average_price)}</Text>
                <Slider minimumValue={100000} maximumValue={2000000} value={drivers.average_price}
                    onValueChange={(v) => { setLastChanged('average_price'); setDrivers({ ...drivers, average_price: v }); }}
                    minimumTrackTintColor={RIZER_COLORS.Indigo} />

                <Text style={styles.sliderLabel}>COGS %: {Math.round(drivers.cost_of_goods_percent)}%</Text>
                <Slider minimumValue={40} maximumValue={80} value={drivers.cost_of_goods_percent}
                    onValueChange={(v) => { setLastChanged('cost_of_goods_percent'); setDrivers({ ...drivers, cost_of_goods_percent: v }); }}
                    minimumTrackTintColor={RIZER_COLORS.Indigo} />

                <Text style={styles.sliderLabel}>Operating Expenses: ₹{Math.round(drivers.operating_expenses)} Cr</Text>
                <Slider minimumValue={1000} maximumValue={20000} value={drivers.operating_expenses}
                    onValueChange={(v) => { setLastChanged('operating_expenses'); setDrivers({ ...drivers, operating_expenses: v }); }}
                    minimumTrackTintColor={RIZER_COLORS.Indigo} />

                <Text style={styles.sliderLabel}>Tax Rate: {Math.round(drivers.tax_rate)}%</Text>
                <Slider minimumValue={15} maximumValue={35} value={drivers.tax_rate}
                    onValueChange={(v) => { setLastChanged('tax_rate'); setDrivers({ ...drivers, tax_rate: v }); }}
                    minimumTrackTintColor={RIZER_COLORS.Indigo} />
            </View>

            <Modal visible={goalModal} transparent animationType="slide">
                <View style={styles.modalContainer}>
                    <View style={styles.modalContent}>
                        <Text style={styles.modalTitle}>Goal Seek Net Profit</Text>
                        <Text style={styles.modalDesc}>What Net Profit (in Cr) do you want?</Text>
                        <TextInput style={styles.input} value={targetProfit} onChangeText={setTargetProfit} keyboardType="numeric" />
                        <TouchableOpacity style={styles.actionBtn} onPress={runGoalSeek}>
                            <Text style={styles.actionBtnText}>Find Sales Volume</Text>
                        </TouchableOpacity>
                        {goalResult && (
                            <View style={styles.goalResultBox}>
                                <Text>Required Volume: <Text style={{ fontWeight: 'bold' }}>{Math.round(goalResult.required_value)}</Text> units</Text>
                                <Text>Achieved Profit: <Text style={{ fontWeight: 'bold' }}>{goalResult.achieved_target} Cr</Text></Text>
                            </View>
                        )}
                        <TouchableOpacity style={[styles.actionBtn, { backgroundColor: RIZER_COLORS.Gray, marginTop: 10 }]} onPress={() => setGoalModal(false)}>
                            <Text style={styles.actionBtnText}>Close</Text>
                        </TouchableOpacity>
                    </View>
                </View>
            </Modal>
        </View>
    );
}

// DIMENSIONS TAB ───────────────────────────────────────────────────────
function DimensionsTab() {
    const [data, setData] = useState<any>(null);
    const [summary, setSummary] = useState("Loading insights...");
    const [loading, setLoading] = useState(false);

    const buildModel = async () => {
        try {
            setLoading(true);
            const res = await fetch(`${API_BASE}/model/build`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dimensions: ["department", "region"], metric: "revenue" })
            });
            const j = await res.json();
            if (j.status === 'success') setData(j.pivot);
            const sumRes = await fetch(`${API_BASE}/model/summary?metric=revenue`);
            const sumj = await sumRes.json();
            if (sumj.status === 'success') setSummary(sumj.summary.insights);
        } catch (e) { console.error(e); } finally { setLoading(false); }
    };

    return (
        <View style={styles.tabSection}>
            <Text style={styles.descText}>Pivot Table: Department x Region (Revenue)</Text>
            <TouchableOpacity style={styles.actionBtn} onPress={buildModel}>
                <Text style={styles.actionBtnText}>{loading ? "Building..." : "Build Model"}</Text>
            </TouchableOpacity>
            {data && <ScrollView horizontal style={styles.tableScroll}><Text style={styles.codeText}>{JSON.stringify(data, null, 2)}</Text></ScrollView>}
            <View style={styles.insightsCard}>
                <Text style={styles.insightsTitle}>💡 AI Insights</Text>
                <Text style={styles.insightsText}>{summary}</Text>
            </View>
        </View>
    );
}

// ROLLING TAB — Ensemble Forecast ────────────────────────────────────
function RollingTab() {
    const [forecast, setForecast] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const fetchForecast = async () => {
        try {
            setLoading(true);
            const res = await fetch(`${API_BASE}/forecast/rolling?metric=revenue&periods=6`);
            const j = await res.json();
            if (j.status === 'success') setForecast(j.forecast);
        } catch (e) { console.error(e); } finally { setLoading(false); }
    };

    useEffect(() => { fetchForecast(); }, []);

    const chartData = {
        labels: forecast ? forecast.predictions.map((p: any) => p.period.substring(5)) : ["1", "2", "3", "4", "5", "6"],
        datasets: [{
            data: forecast ? forecast.predictions.map((p: any) => p.value) : [0, 0, 0, 0, 0, 0],
            color: (opacity = 1) => RIZER_COLORS.Indigo,
            strokeWidth: 2
        }]
    };

    return (
        <View style={styles.tabSection}>
            {/* Model badge */}
            <View style={styles.badgeContainer}>
                <Text style={styles.badgeLabel}>{forecast ? forecast.model_used : 'Loading...'}</Text>
                <Text style={styles.badgeValue}>MAPE {forecast?.accuracy?.mape ?? '?'}%</Text>
            </View>

            {/* Accuracy row */}
            {forecast?.accuracy && (
                <View style={styles.metricsContainer}>
                    <View style={styles.metricCard}>
                        <Text style={styles.metricLabel}>R²</Text>
                        <Text style={styles.metricValue}>{forecast.accuracy.r2}</Text>
                    </View>
                    <View style={styles.metricCard}>
                        <Text style={styles.metricLabel}>RMSE</Text>
                        <Text style={styles.metricValue}>{forecast.accuracy.rmse}</Text>
                    </View>
                    <View style={styles.metricCard}>
                        <Text style={styles.metricLabel}>Growth</Text>
                        <Text style={[styles.metricValue, { color: (forecast.growth_rate || 0) >= 0 ? RIZER_COLORS.Green : RIZER_COLORS.Red }]}>
                            {forecast.growth_rate}%
                        </Text>
                    </View>
                </View>
            )}

            {/* Festival insight */}
            {forecast?.festival_impact && (
                <View style={[styles.insightsCard, { borderTopColor: RIZER_COLORS.Amber }]}>
                    <Text style={styles.insightsTitle}>🎊 Festival Impact</Text>
                    <Text style={styles.insightsText}>{forecast.festival_impact}</Text>
                </View>
            )}

            <Text style={styles.descText}>6-Month Rolling Forecast ({forecast?.data_points_used ?? '?'} data points)</Text>
            {loading ? <ActivityIndicator size="large" color={RIZER_COLORS.Indigo} /> : (
                <ScrollView horizontal>
                    <LineChart data={chartData} width={screenWidth - 20} height={220} yAxisLabel="₹"
                        chartConfig={{ backgroundColor: '#fff', backgroundGradientFrom: '#fff', backgroundGradientTo: '#fff', decimalPlaces: 0, color: (opacity = 1) => `rgba(79, 91, 213, ${opacity})` }}
                        bezier style={styles.chart} />
                </ScrollView>
            )}

            <TouchableOpacity style={styles.actionBtn} onPress={fetchForecast}>
                <Text style={styles.actionBtnText}>Refresh Forecast</Text>
            </TouchableOpacity>
        </View>
    );
}

// BUDGET TAB ──────────────────────────────────────────────────────────
function BudgetTab() {
    const [report, setReport] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const fetchReport = async () => {
        try {
            setLoading(true);
            const res = await fetch(`${API_BASE}/budget/report?year=2024`);
            const j = await res.json();
            if (j.status === 'success') setReport(j.report);
        } catch (e) { console.error(e); } finally { setLoading(false); }
    };

    return (
        <View style={styles.tabSection}>
            <TouchableOpacity style={styles.actionBtn} onPress={fetchReport}>
                <Text style={styles.actionBtnText}>{loading ? "Loading..." : "Full Year Report"}</Text>
            </TouchableOpacity>
            {report && (
                <View style={styles.insightsCard}>
                    <Text style={styles.insightsTitle}>📋 Executive Summary</Text>
                    <Text style={styles.insightsText}>{report.summary}</Text>
                </View>
            )}
            {report?.data?.revenue && (
                <View style={styles.table}>
                    <View style={styles.tableHeader}>
                        <Text style={styles.th}>Month</Text>
                        <Text style={styles.th}>Variance</Text>
                        <Text style={styles.th}>Status</Text>
                    </View>
                    {report.data.revenue.slice(0, 5).map((row: any, idx: number) => (
                        <View key={idx} style={styles.tableRow}>
                            <Text style={styles.td}>Month {idx + 1}</Text>
                            <Text style={styles.td}>{row.variance_pct.toFixed(1)}%</Text>
                            <Text style={styles.td}>{row.rag === 'green' ? '🟢' : row.rag === 'yellow' ? '🟡' : '🔴'}</Text>
                        </View>
                    ))}
                </View>
            )}
        </View>
    );
}

// CONNECT TAB — ERP/CRM Integrations ─────────────────────────────────
const INTEGRATION_CARDS: { key: string; name: string; type: string; icon: string }[] = [
    { key: 'tally', name: 'Tally', type: 'ERP', icon: '📒' },
    { key: 'zoho_books', name: 'Zoho Books', type: 'ERP', icon: '📗' },
    { key: 'quickbooks', name: 'QuickBooks', type: 'ERP', icon: '📘' },
    { key: 'zoho_crm', name: 'Zoho CRM', type: 'CRM', icon: '🤝' },
    { key: 'hubspot', name: 'HubSpot', type: 'CRM', icon: '🧲' },
    { key: 'salesforce', name: 'Salesforce', type: 'CRM', icon: '☁️' },
];

function ConnectTab() {
    const [status, setStatus] = useState<any>(null);
    const [syncing, setSyncing] = useState(false);
    const [logs, setLogs] = useState<any[]>([]);
    const [connectModal, setConnectModal] = useState(false);
    const [selectedSource, setSelectedSource] = useState('');
    const [creds, setCreds] = useState<any>({});

    const fetchStatus = async () => {
        try {
            const res = await fetch(`${API_BASE}/integrations/status`);
            const j = await res.json();
            if (j.status === 'success') setStatus(j.integrations);
        } catch (e) { console.error(e); }
    };

    const fetchLogs = async () => {
        try {
            const res = await fetch(`${API_BASE}/integrations/log`);
            const j = await res.json();
            if (j.status === 'success') setLogs(j.log || []);
        } catch (e) { console.error(e); }
    };

    const triggerSync = async () => {
        try {
            setSyncing(true);
            await fetch(`${API_BASE}/integrations/sync`, { method: 'POST' });
            await fetchStatus();
            await fetchLogs();
        } catch (e) { console.error(e); } finally { setSyncing(false); }
    };

    const submitConnect = async () => {
        try {
            await fetch(`${API_BASE}/integrations/connect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source: selectedSource, ...creds })
            });
            setConnectModal(false);
            setCreds({});
            await fetchStatus();
        } catch (e) { console.error(e); }
    };

    useEffect(() => { fetchStatus(); fetchLogs(); }, []);

    return (
        <View style={styles.tabSection}>
            <TouchableOpacity style={[styles.actionBtn, syncing && { opacity: 0.6 }]} onPress={triggerSync} disabled={syncing}>
                <Text style={styles.actionBtnText}>{syncing ? '⏳ Syncing...' : '🔄 Manual Sync'}</Text>
            </TouchableOpacity>

            {INTEGRATION_CARDS.map(card => {
                const info = status?.[card.key];
                const isConnected = info?.configured && info?.last_status === 'connected';
                return (
                    <View key={card.key} style={styles.integrationCard}>
                        <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
                            <Text style={{ fontSize: 28, marginRight: 10 }}>{card.icon}</Text>
                            <View style={{ flex: 1 }}>
                                <Text style={styles.integrationName}>{card.name}</Text>
                                <Text style={styles.integrationType}>{card.type}</Text>
                                {info?.last_sync && <Text style={{ fontSize: 11, color: RIZER_COLORS.Gray }}>Last sync: {info.last_sync.substring(0, 16)}</Text>}
                            </View>
                        </View>
                        <TouchableOpacity
                            style={[styles.connectBtn, isConnected && { backgroundColor: RIZER_COLORS.Green }]}
                            onPress={() => { if (!isConnected) { setSelectedSource(card.key); setConnectModal(true); } }}
                        >
                            <Text style={styles.connectBtnText}>{isConnected ? '✅ Connected' : 'Connect'}</Text>
                        </TouchableOpacity>
                    </View>
                );
            })}

            {/* Sync Log */}
            {logs.length > 0 && (
                <View style={styles.table}>
                    <Text style={[styles.insightsTitle, { marginBottom: 10 }]}>📋 Sync Log</Text>
                    {logs.slice(0, 5).map((log: any, i: number) => (
                        <View key={i} style={styles.tableRow}>
                            <Text style={[styles.td, { flex: 2 }]}>{log.source}</Text>
                            <Text style={styles.td}>{log.status}</Text>
                            <Text style={styles.td}>{log.records_added}r</Text>
                        </View>
                    ))}
                </View>
            )}

            {/* Connect Modal */}
            <Modal visible={connectModal} transparent animationType="slide">
                <View style={styles.modalContainer}>
                    <View style={styles.modalContent}>
                        <Text style={styles.modalTitle}>Connect {selectedSource}</Text>
                        <TextInput style={styles.input} placeholder="Client ID / API Key" placeholderTextColor="#999"
                            value={creds.client_id || creds.api_key || creds.token || ''} onChangeText={v => setCreds({ ...creds, client_id: v, api_key: v, token: v })} />
                        <TextInput style={styles.input} placeholder="Client Secret (if required)" placeholderTextColor="#999"
                            value={creds.client_secret || ''} onChangeText={v => setCreds({ ...creds, client_secret: v })} />
                        <TouchableOpacity style={styles.actionBtn} onPress={submitConnect}>
                            <Text style={styles.actionBtnText}>Test & Save</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={[styles.actionBtn, { backgroundColor: RIZER_COLORS.Gray }]} onPress={() => setConnectModal(false)}>
                            <Text style={styles.actionBtnText}>Cancel</Text>
                        </TouchableOpacity>
                    </View>
                </View>
            </Modal>
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: RIZER_COLORS.LightGray },
    headerTitle: { fontSize: 24, fontWeight: 'bold', color: RIZER_COLORS.Navy, padding: 20, paddingTop: 60, backgroundColor: RIZER_COLORS.White },
    tabScroll: { backgroundColor: RIZER_COLORS.White, maxHeight: 50 },
    tabContainer: { flexDirection: 'row', backgroundColor: RIZER_COLORS.White, paddingBottom: 10 },
    tabButton: { paddingVertical: 10, paddingHorizontal: 18, alignItems: 'center', borderBottomWidth: 2, borderBottomColor: 'transparent' },
    activeTab: { borderBottomColor: RIZER_COLORS.Indigo },
    tabText: { color: RIZER_COLORS.Gray, fontWeight: 'bold', fontSize: 13 },
    activeTabText: { color: RIZER_COLORS.Indigo },
    content: { padding: 20 },
    tabSection: { paddingBottom: 40 },

    metricsContainer: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20, borderRadius: 8 },
    metricCard: { flex: 1, backgroundColor: RIZER_COLORS.White, padding: 10, borderRadius: 8, marginHorizontal: 4, elevation: 2 },
    metricLabel: { fontSize: 12, color: RIZER_COLORS.Gray, marginBottom: 5 },
    metricValue: { fontSize: 16, fontWeight: 'bold', color: RIZER_COLORS.Navy },

    cascadeBox: { backgroundColor: '#FFF8E1', padding: 15, borderRadius: 8, borderLeftWidth: 4, borderLeftColor: RIZER_COLORS.Amber, marginBottom: 15 },
    cascadeTitle: { fontWeight: 'bold', color: RIZER_COLORS.Navy, marginBottom: 8 },
    cascadePath: { fontSize: 13, color: '#555', marginBottom: 3, fontFamily: 'monospace' },
    cascadeChange: { fontSize: 13, fontWeight: 'bold', marginTop: 2 },

    sliderSection: { backgroundColor: RIZER_COLORS.White, padding: 20, borderRadius: 12, elevation: 1, marginTop: 20 },
    sliderLabel: { marginTop: 15, marginBottom: 5, fontWeight: '600', color: RIZER_COLORS.Navy },

    actionBtn: { backgroundColor: RIZER_COLORS.Indigo, padding: 15, borderRadius: 8, alignItems: 'center', marginVertical: 10 },
    actionBtnText: { color: RIZER_COLORS.White, fontWeight: 'bold', fontSize: 16 },

    modalContainer: { flex: 1, justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.5)', padding: 20 },
    modalContent: { backgroundColor: RIZER_COLORS.White, padding: 20, borderRadius: 12 },
    modalTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 10 },
    modalDesc: { color: RIZER_COLORS.Gray, marginBottom: 15 },
    input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 12, marginBottom: 12 },
    goalResultBox: { marginTop: 20, padding: 15, backgroundColor: RIZER_COLORS.LightGray, borderRadius: 8 },

    insightsCard: { backgroundColor: RIZER_COLORS.White, padding: 20, borderRadius: 12, elevation: 1, marginTop: 20, borderTopWidth: 4, borderTopColor: RIZER_COLORS.Amber },
    insightsTitle: { fontSize: 16, fontWeight: 'bold', marginBottom: 10, color: RIZER_COLORS.Navy },
    insightsText: { lineHeight: 22, color: '#333' },

    badgeContainer: { flexDirection: 'row', justifyContent: 'space-between', backgroundColor: RIZER_COLORS.Navy, padding: 15, borderRadius: 8, marginBottom: 20 },
    badgeLabel: { color: RIZER_COLORS.White, fontSize: 14, flex: 1 },
    badgeValue: { color: RIZER_COLORS.Amber, fontSize: 20, fontWeight: 'bold' },

    descText: { marginVertical: 10, color: RIZER_COLORS.Gray, fontSize: 14, fontWeight: 'bold' },
    chart: { marginVertical: 8, borderRadius: 16 },

    tableScroll: { backgroundColor: RIZER_COLORS.White, padding: 10, borderRadius: 8, maxHeight: 200 },
    codeText: { fontFamily: 'monospace', fontSize: 12 },

    table: { backgroundColor: RIZER_COLORS.White, borderRadius: 8, padding: 10, marginTop: 20 },
    tableHeader: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: '#ddd', paddingBottom: 10, marginBottom: 10 },
    th: { flex: 1, fontWeight: 'bold', color: RIZER_COLORS.Navy },
    tableRow: { flexDirection: 'row', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#eee' },
    td: { flex: 1, color: '#333' },

    integrationCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: RIZER_COLORS.White, padding: 15, borderRadius: 10, marginVertical: 5, elevation: 1 },
    integrationName: { fontWeight: 'bold', fontSize: 15, color: RIZER_COLORS.Navy },
    integrationType: { fontSize: 12, color: RIZER_COLORS.Gray },
    connectBtn: { backgroundColor: RIZER_COLORS.Indigo, paddingHorizontal: 15, paddingVertical: 8, borderRadius: 6 },
    connectBtnText: { color: RIZER_COLORS.White, fontWeight: 'bold', fontSize: 13 },
});
