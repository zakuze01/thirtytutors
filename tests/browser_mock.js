window.__qa={messages:[],microphoneCalls:0,streams:[],contexts:[]};
class QASocket {
 static OPEN=1;
 constructor(){this.readyState=1;window.__qa.socket=this;queueMicrotask(()=>this.onopen?.({}));}
 send(raw){const m=JSON.parse(raw);window.__qa.messages.push(m.type);
 if(m.type==='init')queueMicrotask(()=>this.onmessage?.({data:JSON.stringify({type:'session_status',mode:document.getElementById('mode').value,resumed:false})}));
 if(m.type==='policy_change'){queueMicrotask(()=>this.onmessage?.({data:JSON.stringify({type:'policy_pending'})}));setTimeout(()=>this.onmessage?.({data:JSON.stringify({type:'session_status',mode:m.policy.mode,resumed:false})}),10);}
 if(m.type==='turn_complete')setTimeout(()=>this.onmessage?.({data:JSON.stringify({type:'turn_complete'})}),10);
 }
 close(){this.readyState=3;queueMicrotask(()=>this.onclose?.({}));}
}
window.WebSocket=QASocket;
navigator.mediaDevices.getUserMedia=async()=>{window.__qa.microphoneCalls++;const ctx=new AudioContext();const dest=ctx.createMediaStreamDestination();const osc=ctx.createOscillator();osc.connect(dest);osc.start();await ctx.resume();window.__qa.streams.push(dest.stream);window.__qa.contexts.push(ctx);return dest.stream;};
