import {useCallback,useState} from 'react';
import {useFocusEffect} from 'expo-router';
import {Text} from 'react-native';
import {Button,Card,Copy,Screen,Title} from '../services/ui';
import {outbox,getMeta} from '../services/database';
import {useSession} from '../services/session';
export default function SyncScreen(){const {user,sync,syncing,status,version}=useSession();const [ops,O]=useState<any[]>([]),[last,L]=useState('');useFocusEffect(useCallback(()=>{if(user){outbox(user.id).then(O);getMeta(user.id,'last_sync').then(x=>L(x||''))}},[user,version]));return <Screen><Title>Synchronization</Title><Copy>{status}</Copy><Copy>Last successful sync: {last?new Date(last).toLocaleString():'Never'}</Copy><Button label={syncing?'Synchronizing…':'Sync now'} disabled={!user||syncing} onPress={()=>sync()}/><Title>{ops.length} pending changes</Title>{ops.length===0?<Copy>No changes waiting to sync.</Copy>:ops.map(op=><Card key={op.id}><Text style={{fontWeight:'700'}}>{op.kind==='patient_create'?'New patient':'Medical record'}</Text><Copy>{op.error?'Needs attention: '+op.error:'Waiting to sync'}</Copy></Card>)}<Copy>Failed changes remain on this device. Sign in online again if your session has expired.</Copy></Screen>}
