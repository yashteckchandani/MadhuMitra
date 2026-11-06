const base=(process.env.EXPO_PUBLIC_API_BASE_URL || 'http://10.0.2.2:8000').replace(/\/$/,'');
export async function request(path:string, token?:string, options:RequestInit={}) {
  const controller = new AbortController();
  const timer=setTimeout(()=>controller.abort(),15000);
  try {
    const response=await fetch(base+'/api/v1'+path,{...options,signal:controller.signal,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})}});
    const data=await response.json().catch(()=>({}));
    if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'Request failed');
    return data;
  } finally { clearTimeout(timer); }
}
