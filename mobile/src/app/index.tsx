import {Link} from 'expo-router';
import {Brand,Button,Card,Copy,Screen,Title} from '../services/ui';
import {useSession} from '../services/session';
export default function Home(){const {ready}=useSession();return <Screen><Brand/><Title>Connected Diabetes Care</Title><Copy>A shared view of patient histories for the people caring for rural communities.</Copy><Card><Copy>Previously saved records can be accessed on this device after an online sign-in and offline PIN setup.</Copy></Card><Link href="/login" asChild><Button label={ready?'Get started':'Preparing local storage…'} disabled={!ready}/></Link></Screen>}
