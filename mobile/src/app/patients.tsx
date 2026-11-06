import {useCallback,useState} from 'react';
import {router,useFocusEffect} from 'expo-router';
import {Pressable,Text} from 'react-native';
import {Button,Card,Copy,Input,Screen,Title} from '../services/ui';
import {useSession} from '../services/session';
import {listPatients} from '../services/database';
export default function Patients(){const {user,version}=useSession();const [rows,R]=useState<any[]>([]),[query,Q]=useState('');useFocusEffect(useCallback(()=>{if(user)listPatients(user.id).then(R)},[user,version]));if(!user)return <Screen><Copy>Sign in first.</Copy></Screen>;const filtered=rows.filter(x=>(x.name+' '+x.patient_id).toLowerCase().includes(query.toLowerCase()));return <Screen><Title>Patients</Title><Copy>Available on this device · {filtered.length} patients</Copy><Input label="Search by name or patient ID" value={query} onChangeText={Q}/><Button label="Enroll patient" onPress={()=>router.push('/new-patient')}/>{filtered.map(p=><Pressable key={p.patient_id} onPress={()=>router.push({pathname:'/patient/[id]',params:{id:p.patient_id}})}><Card><Text style={{fontWeight:'700'}}>{p.name} · {p.priority}</Text><Copy>{p.patient_id} · {p.village}</Copy>{p.pending&&<Copy>Saved on this device · Waiting to sync</Copy>}</Card></Pressable>)}</Screen>}
