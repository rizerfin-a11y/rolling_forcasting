// frontend/screens/AIChatScreen.tsx
// The AI chat screen that connects to the memory system
import React, { useState, useRef, useEffect } from 'react';
import {
    View, Text, TextInput, TouchableOpacity, FlatList,
    StyleSheet, ActivityIndicator, KeyboardAvoidingView,
    Platform, Animated
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API = process.env.EXPO_PUBLIC_API_URL;

interface Message {
    id: string;
    role: 'user' | 'ai';
    text: string;
    confidence?: 'high' | 'medium' | 'low';
    timestamp: Date;
    isLoading?: boolean;
}

const QUICK_QUESTIONS = [
    "What was revenue last year?",
    "Am I profitable?",
    "What are my biggest expenses?",
    "How is my cash flow?",
    "What should I improve?",
];

export default function AIChatScreen() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [language, setLanguage] = useState<'english' | 'tamil' | 'hindi'>('english');
    const [learnMode, setLearnMode] = useState(false);
    const flatListRef = useRef<FlatList>(null);

    useEffect(() => {
        // Welcome message
        setMessages([{
            id: '0',
            role: 'ai',
            text: "Hello! I am your AI financial advisor. I have access to your complete financial history and can answer questions in English, Tamil, or Hindi. What would you like to know?",
            timestamp: new Date(),
        }]);
    }, []);

    const sendMessage = async (text: string) => {
        if (!text.trim() || loading) return;
        const userMsg: Message = {
            id: Date.now().toString(),
            role: 'user', text,
            timestamp: new Date()
        };
        const loadingMsg: Message = {
            id: (Date.now() + 1).toString(),
            role: 'ai', text: '',
            timestamp: new Date(), isLoading: true
        };
        setMessages(prev => [...prev, userMsg, loadingMsg]);
        setInput('');
        setLoading(true);
        setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);

        try {
            const token = await AsyncStorage.getItem('access_token');
            const companyName = await AsyncStorage.getItem('company_name') || 'My Business';
            const res = await fetch(`${API}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    question: text,
                    language,
                    company_name: companyName,
                    learn_mode: learnMode
                }),
            });
            const data = await res.json();
            setMessages(prev => [
                ...prev.filter(m => !m.isLoading),
                {
                    id: Date.now().toString(),
                    role: 'ai',
                    text: data.answer || "I couldn't find an answer. Please try again.",
                    confidence: data.confidence,
                    timestamp: new Date(),
                }
            ]);
        } catch {
            setMessages(prev => [
                ...prev.filter(m => !m.isLoading),
                {
                    id: Date.now().toString(), role: 'ai',
                    text: "Connection error. Please check your internet.", timestamp: new Date()
                }
            ]);
        } finally {
            setLoading(false);
            setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 200);
        }
    };

    const renderMessage = ({ item }: { item: Message }) => {
        const isUser = item.role === 'user';
        const confidenceColor = item.confidence === 'high' ? '#0F6E56'
            : item.confidence === 'medium' ? '#854F0B' : '#A32D2D';
        return (
            <View style={[styles.msgRow, isUser && styles.msgRowUser]}>
                {!isUser && (
                    <View style={styles.avatar}>
                        <Text style={styles.avatarText}>AI</Text>
                    </View>
                )}
                <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAI]}>
                    {item.isLoading ? (
                        <View style={styles.loadingRow}>
                            <ActivityIndicator size="small" color="#185FA5" />
                            <Text style={styles.loadingText}>Analysing your financial data...</Text>
                        </View>
                    ) : (
                        <>
                            <Text style={[styles.msgText, isUser && styles.msgTextUser]}>
                                {item.text}
                            </Text>
                            {item.confidence && (
                                <Text style={[styles.confidenceBadge, { color: confidenceColor }]}>
                                    {item.confidence === 'high' ? '● High confidence'
                                        : item.confidence === 'medium' ? '● Medium confidence'
                                            : '● Low confidence — add more data'}
                                </Text>
                            )}
                        </>
                    )}
                </View>
            </View>
        );
    };

    return (
        <KeyboardAvoidingView
            style={styles.container}
            behavior={Platform.OS === 'ios' ? 'padding' : undefined}
            keyboardVerticalOffset={90}
        >
            {/* Language selector */}
            <View style={styles.langRow}>
                {(['english', 'tamil', 'hindi'] as const).map(lang => (
                    <TouchableOpacity
                        key={lang}
                        style={[styles.langBtn, language === lang && styles.langBtnActive]}
                        onPress={() => setLanguage(lang)}
                    >
                        <Text style={[styles.langText, language === lang && styles.langTextActive]}>
                            {lang === 'english' ? 'English' : lang === 'tamil' ? 'தமிழ்' : 'हिंदी'}
                        </Text>
                    </TouchableOpacity>
                ))}
            </View>

            {/* Mode Selector */}
            <View style={styles.modeRow}>
                <TouchableOpacity
                    style={[styles.modeBtn, !learnMode && styles.modeBtnActive]}
                    onPress={() => setLearnMode(false)}
                >
                    <Text style={[styles.modeText, !learnMode && styles.modeTextActive]}>Expert Mode</Text>
                </TouchableOpacity>
                <TouchableOpacity
                    style={[styles.modeBtn, learnMode && styles.modeBtnActive]}
                    onPress={() => setLearnMode(true)}
                >
                    <Text style={[styles.modeText, learnMode && styles.modeTextActive]}>🎓 Learn Mode</Text>
                </TouchableOpacity>
            </View>

            {/* Messages */}
            <FlatList
                ref={flatListRef}
                data={messages}
                renderItem={renderMessage}
                keyExtractor={m => m.id}
                contentContainerStyle={styles.messageList}
                showsVerticalScrollIndicator={false}
            />

            {/* Quick question chips */}
            {messages.length <= 2 && (
                <View style={styles.quickRow}>
                    {QUICK_QUESTIONS.slice(0, 3).map(q => (
                        <TouchableOpacity key={q} style={styles.quickChip} onPress={() => sendMessage(q)}>
                            <Text style={styles.quickText}>{q}</Text>
                        </TouchableOpacity>
                    ))}
                </View>
            )}

            {/* Input bar */}
            <View style={styles.inputBar}>
                <TextInput
                    style={styles.input}
                    value={input}
                    onChangeText={setInput}
                    placeholder={language === 'tamil' ? 'உங்கள் கேள்வியை கேளுங்கள்...'
                        : language === 'hindi' ? 'अपना सवाल पूछें...'
                            : 'Ask about your finances...'}
                    placeholderTextColor="#888780"
                    multiline
                    maxLength={500}
                    onSubmitEditing={() => sendMessage(input)}
                />
                <TouchableOpacity
                    style={[styles.sendBtn, (!input.trim() || loading) && styles.sendBtnDisabled]}
                    onPress={() => sendMessage(input)}
                    disabled={!input.trim() || loading}
                >
                    <Text style={styles.sendText}>→</Text>
                </TouchableOpacity>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#FFFFFF' },
    langRow: { flexDirection: 'row', padding: 10, gap: 8, borderBottomWidth: 0.5, borderBottomColor: '#D3D1C7' },
    langBtn: { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 16, borderWidth: 1, borderColor: '#D3D1C7' },
    langBtnActive: { backgroundColor: '#0C2340', borderColor: '#0C2340' },
    langText: { fontSize: 13, color: '#5F5E5A' },
    langTextActive: { color: '#FFFFFF', fontWeight: '500' },
    modeRow: { flexDirection: 'row', paddingHorizontal: 16, paddingVertical: 8, gap: 10, backgroundColor: '#F9FAFC' },
    modeBtn: { flex: 1, paddingVertical: 8, borderRadius: 8, alignItems: 'center', backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#D3D1C7' },
    modeBtnActive: { backgroundColor: '#185FA5', borderColor: '#185FA5' },
    modeText: { fontSize: 13, color: '#1B2B6B', fontWeight: '500' },
    modeTextActive: { color: '#FFFFFF' },
    messageList: { padding: 16, paddingBottom: 8 },
    msgRow: { flexDirection: 'row', marginBottom: 14, alignItems: 'flex-end', gap: 8 },
    msgRowUser: { flexDirection: 'row-reverse' },
    avatar: { width: 32, height: 32, borderRadius: 16, backgroundColor: '#185FA5', justifyContent: 'center', alignItems: 'center' },
    avatarText: { color: '#FFFFFF', fontSize: 11, fontWeight: '600' },
    bubble: { maxWidth: '80%', borderRadius: 14, padding: 12 },
    bubbleAI: { backgroundColor: '#F1EFE8', borderBottomLeftRadius: 4 },
    bubbleUser: { backgroundColor: '#185FA5', borderBottomRightRadius: 4 },
    msgText: { fontSize: 14, color: '#1a1a1a', lineHeight: 20 },
    msgTextUser: { color: '#FFFFFF' },
    confidenceBadge: { fontSize: 10, marginTop: 6, fontWeight: '500' },
    loadingRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    loadingText: { fontSize: 12, color: '#5F5E5A' },
    quickRow: { paddingHorizontal: 14, paddingBottom: 8, gap: 6 },
    quickChip: { backgroundColor: '#E6F1FB', borderRadius: 16, paddingHorizontal: 12, paddingVertical: 7, marginBottom: 4 },
    quickText: { fontSize: 12, color: '#185FA5' },
    inputBar: { flexDirection: 'row', padding: 12, borderTopWidth: 0.5, borderTopColor: '#D3D1C7', gap: 8, alignItems: 'flex-end' },
    input: { flex: 1, backgroundColor: '#F1EFE8', borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, fontSize: 14, maxHeight: 100, color: '#1a1a1a' },
    sendBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#185FA5', justifyContent: 'center', alignItems: 'center' },
    sendBtnDisabled: { backgroundColor: '#D3D1C7' },
    sendText: { color: '#FFFFFF', fontSize: 18, fontWeight: '600' },
});