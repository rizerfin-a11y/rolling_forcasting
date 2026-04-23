import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { View, Text } from 'react-native';

import AIChatScreen from './screens/AIChatScreen';
import ForecastScreen from './screens/ForecastScreen';
import ModelScreen from './screens/ModelScreen';

const Tab = createBottomTabNavigator();

function DummyScreen({ title }: { title: string }) {
    return (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
            <Text>{title}</Text>
        </View>
    );
}

export default function App() {
    return (
        <NavigationContainer>
            <Tab.Navigator screenOptions={{ headerShown: false }}>
                <Tab.Screen name="Chat" component={AIChatScreen} options={{ tabBarLabel: '💬 Chat' }} />
                <Tab.Screen name="Forecast" component={ForecastScreen} options={{ tabBarLabel: '📈 Forecast' }} />
                <Tab.Screen name="Models" component={ModelScreen} options={{ tabBarLabel: '⚙️ Models' }} />
                <Tab.Screen name="Alerts" component={() => <DummyScreen title="Alerts Screen" />} options={{ tabBarLabel: '🔔 Alerts' }} />
                <Tab.Screen name="Profile" component={() => <DummyScreen title="Profile Screen" />} options={{ tabBarLabel: '👤 Profile' }} />
            </Tab.Navigator>
        </NavigationContainer>
    );
}
