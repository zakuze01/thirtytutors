// Inject before page load for QA only. No physical mic, audio or provider requests.
window.__qa={messages:[],microphoneCalls:0,streams:[],sources:[],defer:false,deny:false};
class QASocket{
 static OPEN=1;
 constructor(){this.readyState=1;this.bufferedAmount=0;window.__qa.socket=this;queueMicrotask(()=>this.onopen?.({}));}
 send(raw){const m=JSON.parse(raw);window.__qa.messages.push(m);
  if(m.type==='init')queueMicrotask(()=>this.onmessage?.({data:JSON.stringify({type:'session_status',mode:'friend',resumed:true})}));
  if(m.type==='policy_change'){queueMicrotask(()=>this.onmessage?.({data:JSON.stringify({type:'policy_pending'})}));setTimeout(()=>this.onmessage?.({data:JSON.stringify({type:'session_status',mode:m.policy.mode,resumed:true})}),5);}
 }
 close(){this.readyState=3;queueMicrotask(()=>this.onclose?.({}));}
}
function qaNode(){return {connect(){},disconnect(){}};}
class QAContext{
 constructor(opts={}){this.sampleRate=opts.sampleRate||16000;this.state='running';this.currentTime=0;this.destination=qaNode();this.audioWorklet={addModule:async()=>{}};}
 async resume(){this.state='running';}
 async close(){this.state='closed';}
 createMediaStreamSource(){return qaNode();}
 createAnalyser(){return {...qaNode(),frequencyBinCount:128,getByteTimeDomainData:a=>a.fill(128)};}
 createGain(){return {...qaNode(),gain:{value:1,setValueAtTime(){},linearRampToValueAtTime(){}}};}
 createBuffer(ch,len,rate){return {duration:len/rate,getChannelData:()=>new Float32Array(len)};}
 createBufferSource(){const source={...qaNode(),start(){},stop(){this.stopped=true;this.onended?.();}};window.__qa.sources.push(source);return source;}
}
class QAWorklet{constructor(){this.port={onmessage:null};}connect(){}disconnect(){}}
window.WebSocket=QASocket;window.AudioContext=QAContext;window.AudioWorkletNode=QAWorklet;
navigator.mediaDevices.getUserMedia=async()=>{
 window.__qa.microphoneCalls++;
 if(window.__qa.deny)throw new Error('synthetic permission denied');
 const track={readyState:'live',stop(){this.readyState='ended';}};
 const stream={getTracks:()=>[track]};window.__qa.streams.push(stream);
 if(window.__qa.defer)return new Promise(resolve=>window.__qa.resolvePermission=()=>resolve(stream));
 return stream;
};
