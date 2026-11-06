import {Stack} from 'expo-router';
import {SessionProvider} from '../services/session';
export default function Layout(){return <SessionProvider><Stack screenOptions={{headerTintColor:'#087e71',headerTitle:'MadhuMitra',headerShadowVisible:false}}/></SessionProvider>}
