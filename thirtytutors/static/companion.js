// Voice-only UI over the existing REST and Gemini relay protocol.
// PCM conversion, 16/24 kHz formats and edge fades follow upstream audio.js.
'use strict';
const $ = id => document.getElementById(id);
let profileId = localStorage.getItem('companionProfile') || '';
let conversationId = '', socket = null, retryTimer = null, connected = false;
let capture = null, recording = false, pendingPress = false, pressGeneration = 0;
let playback = null, playbackBus = null, nextPlayback = 0, sources = new Set();
let micAnalyser = null, playbackAnalyser = null, mutedUntilTurn = false;
let activeTranscript = {}, reconnectDelay = 2000;
let editingMemoryId = null;
const status = text => { $('status').textContent = text; };
async function api(path, method = 'GET', data) {
  const response = await fetch(path, {method, headers: {'Content-Type':'application/json'}, body: data === undefined ? undefined : JSON.stringify(data)});
  if (!response.ok) throw new Error(`Yêu cầu không thành công (${response.status}).`);
  return response.json();
}
function option(select, value, label) { const el = document.createElement('option'); el.value = value; el.textContent = label; select.append(el); }
function basePath() { return `/api/profiles/${encodeURIComponent(profileId)}/conversations`; }
function addTranscript(role, text, streaming = false) {
  let item = streaming ? activeTranscript[role] : null;
  if (!item) {
    const row = document.createElement('div'); row.className = 'turn';
    const label = document.createElement('strong'); label.textContent = role === 'user' ? 'Bạn' : 'AI';
    item = document.createElement('span'); row.append(label, item); $('transcript').append(row);
    if (streaming) activeTranscript[role] = item;
  }
  item.textContent += text; item.scrollIntoView({block:'nearest'});
}
async function loadHistory() {
  if (!profileId) return;
  const data = await api(basePath()); $('history').replaceChildren();
  for (const conv of data.conversations) {
    const b = document.createElement('button'); b.textContent = conv.name || 'Cuộc trò chuyện';
    b.onclick = () => chooseConversation(conv.id).catch(showError);
    const remove=document.createElement('button');remove.textContent='Xóa';remove.setAttribute('aria-label','Xóa '+(conv.name||'cuộc trò chuyện'));
    remove.onclick=async()=>{if(!confirm('Xóa hội thoại, transcript, summary và từ mới liên quan?'))return;try{disconnect();await api(`${basePath()}/${conv.id}`,'DELETE');conversationId='';$('transcript').replaceChildren();await loadHistory();status('Đã xóa hội thoại.');}catch(err){showError(err);}};
    const row=document.createElement('div');row.className='history-row';row.append(b,remove);$('history').append(row);
  }
  return data;
}
async function chooseConversation(id) {
  disconnect(); conversationId = id;
  const conv = await api(`${basePath()}/${encodeURIComponent(id)}`);
  $('transcript').replaceChildren(); activeTranscript = {};
  for (const turn of conv.turns) addTranscript(turn.role, turn.text);
  $('voice').value = conv.config.voice_name; $('model').value = conv.config.model_name;
  $('difficulty').value = conv.config.difficulty;
  $('mode').value = conv.config.mode || 'friend'; $('replyLanguage').value = conv.config.reply_language_preference || 'balanced';
  $('correction').value = conv.config.correction_intensity || 'gentle'; $('pace').value = conv.config.speech_pace || 'natural';
  $('remember').checked = conv.config.memory_policy === 'allowed'; $('scenario').value=conv.config.scenario || 'free_learning';
  const profile=await api(`/api/profiles/${profileId}`);$('nickname').value=profile.name;
  if(profile.mic_device_id && !$('mic').querySelector(`option[value="${CSS.escape(profile.mic_device_id)}"]`))option($('mic'),profile.mic_device_id,profile.mic_label||'Micro đã lưu');
  $('mic').value=profile.mic_device_id || '';
  if(profile.speaker_device_id && ![...$('speaker').options].some(o=>o.value===profile.speaker_device_id))option($('speaker'),profile.speaker_device_id,'Loa đã lưu');
  $('speaker').value=profile.speaker_device_id || '';
  await api(`/api/profiles/${profileId}`,'PUT',{active_conversation_id:id});
  status('Sẵn sàng · Micro đang tắt');
}
async function newConversation() {
  if (!profileId) { $('settings').showModal(); return; }
  const conv = await api(basePath(), 'POST', {voice_name:$('voice').value, model_name:$('model').value, ...selectedPolicy(), scenario:$('scenario').value, native_language:'Vietnamese', target_language:'English'});
  await loadHistory(); await chooseConversation(conv.id);
}
function disconnect() {
  clearTimeout(retryTimer); connected = false; $('talk').disabled = true;
  stopRecording(); stopAudio();
  if (socket) { socket.manual = true; socket.close(); socket = null; }
}
function connect() {
  if (!conversationId) return;
  disconnect(); status('Đang kết nối đến Gemini');
  const s = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/session`); socket = s;
  s.onopen = () => s.send(JSON.stringify({type:'init', profile_id:profileId, conversation_id:conversationId}));
  s.onmessage = event => {
    if (s !== socket) return;
    const msg = JSON.parse(event.data);
    if (msg.type === 'session_status') {
      connected = !msg.unavailable; $('talk').disabled = !connected;
      if (connected) { reconnectDelay = 2000; mutedUntilTurn=false; $('mode').value=msg.mode || 'friend'; policyControls(false); status('Listening · Sẵn sàng'); if(!$('transcript').childElementCount && !msg.resumed)send({type:'session_open'}); }
    } else if (msg.type === 'policy_pending') { connected=false; $('talk').disabled=true; status('Reconnecting · Đang đổi chế độ');
    } else if (msg.type === 'audio') { if (!mutedUntilTurn) playAudio(msg.data).catch(showError); }
    else if (msg.type === 'interrupted') { stopAudio(); mutedUntilTurn = false; }
    else if (msg.type === 'quiz_resume') send({type:'quiz_skip',quiz_id:msg.quiz_id});
    else if (msg.type === 'transcript_in') addTranscript('user', msg.text, true);
    else if (msg.type === 'transcript_out') addTranscript('model', msg.text, true);
    else if (msg.type === 'turn_complete') { activeTranscript = {}; mutedUntilTurn = false; status('Listening · Sẵn sàng'); loadHistory().catch(showError); }
    else if (msg.type === 'error') { status('Error · ' + msg.message); }
    else if (msg.type === 'waiting_long') status(msg.active ? 'Thinking · Đang chờ Gemini' : 'Đã kết nối');
  };
  s.onerror = () => status('Error · Không thể kết nối. Chọn Retry.');
  s.onclose = () => {
    if (s !== socket || s.manual) return;
    connected = false; $('talk').disabled = true; policyControls(false); stopRecording(); stopAudio();
    status('Reconnecting · Chọn Retry để thử ngay');
    retryTimer = setTimeout(connect, reconnectDelay); reconnectDelay = Math.min(30000, reconnectDelay * 2);
  };
}
function send(msg) { if (socket?.readyState === WebSocket.OPEN && connected) socket.send(JSON.stringify(msg)); }
function selectedPolicy() { return {mode:$('mode').value,reply_language_preference:$('replyLanguage').value,correction_intensity:$('correction').value,difficulty:$('difficulty').value,speech_pace:$('pace').value,memory_policy:$('remember').checked?'allowed':'off'}; }
function policyControls(disabled){for(const id of ['mode','replyLanguage','correction','pace','remember'])$(id).disabled=disabled;}
async function changePolicy() {
  if (!conversationId) return;
  if (!connected) {try{await api(`${basePath()}/${conversationId}`,'PUT',selectedPolicy());status('Đã lưu. Kết nối để bắt đầu.');}catch(err){showError(err);}return;}
  stopRecording();stopAudio();send({type:'policy_change',policy:selectedPolicy()});policyControls(true);status('Đang yêu cầu đổi chính sách...');
}
for(const id of ['mode','replyLanguage','correction','pace','remember'])$(id).addEventListener('change',changePolicy);
function encodePCM(samples) {
  const pcm = new Int16Array(samples.length);
  for (let i = 0; i < samples.length; i++) { const v = Math.max(-1, Math.min(1, samples[i])); pcm[i] = v < 0 ? v * 32768 : v * 32767; }
  const bytes = new Uint8Array(pcm.buffer); let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}
async function startRecording() {
  if (pendingPress || recording || !connected) return;
  pendingPress = true; const generation = ++pressGeneration;
  let stream, ctx;
  try {
    stream = await navigator.mediaDevices.getUserMedia({audio: {deviceId: $('mic').value ? {exact:$('mic').value} : undefined, echoCancellation:true, noiseSuppression:true}});
    if (!pendingPress || generation !== pressGeneration || !connected) { stream.getTracks().forEach(t => t.stop()); return; }
    ctx = new AudioContext({sampleRate:16000}); await ctx.resume();
    await ctx.audioWorklet.addModule('/pcm-processor.js');
    if (!pendingPress || generation !== pressGeneration || !connected) { stream.getTracks().forEach(t=>t.stop()); await ctx.close(); return; }
    stopAudio(); mutedUntilTurn = false; activeTranscript = {};
    const worklet = new AudioWorkletNode(ctx, 'pcm-capture-processor');
    const input = ctx.createMediaStreamSource(stream); micAnalyser = ctx.createAnalyser();
    input.connect(micAnalyser); input.connect(worklet);
    const silent = ctx.createGain(); silent.gain.value = 0; worklet.connect(silent); silent.connect(ctx.destination);
    capture = {stream, ctx, worklet}; recording = true;
    ensureWave();
    send({type:'start_turn'});
    worklet.port.onmessage = event => { if (recording && generation === pressGeneration) send({type:'audio_chunk', data:encodePCM(event.data)}); };
    $('talk').classList.add('recording'); $('micStatus').textContent = 'Micro đang bật'; status('Listening · Đang nghe');
  } catch (err) {
    stream?.getTracks().forEach(t=>t.stop()); if (ctx && ctx.state !== 'closed') await ctx.close();
    showError(new Error('Không mở được micro. Kiểm tra quyền micro trong Windows rồi thử lại.'));
  } finally { if (generation === pressGeneration) pendingPress = false; }
}
function stopRecording() {
  pendingPress = false; pressGeneration++;
  if (recording) { recording = false; send({type:'turn_complete'}); status('Thinking · Đang chờ'); }
  if (capture) { capture.worklet.port.onmessage = null; capture.stream.getTracks().forEach(t=>t.stop()); capture.ctx.close().catch(()=>{}); capture = null; }
  micAnalyser = null; $('talk').classList.remove('recording'); $('micStatus').textContent = 'Micro đang tắt';
}
async function playAudio(encoded) {
  if (!playback) {
    playback = new AudioContext({sampleRate:24000}); playbackBus = playback.createGain(); playbackAnalyser = playback.createAnalyser();
    playbackBus.connect(playbackAnalyser); playbackAnalyser.connect(playback.destination);
    if($('speaker').value){if(playback.setSinkId)await playback.setSinkId($('speaker').value);else status('WebView2 không hỗ trợ chọn loa riêng. Dùng cài đặt Windows.');}
  }
  await playback.resume(); if (mutedUntilTurn || $('mute').checked) return;
  const bytes = Uint8Array.from(atob(encoded), c => c.charCodeAt(0)); const pcm = new Int16Array(bytes.buffer);
  const buffer = playback.createBuffer(1, pcm.length, 24000); const floats = buffer.getChannelData(0);
  for (let i = 0; i < pcm.length; i++) floats[i] = pcm[i] / 32768;
  const source = playback.createBufferSource(); source.buffer = buffer; const gain = playback.createGain(); source.connect(gain); gain.connect(playbackBus);
  const when = Math.max(nextPlayback, playback.currentTime), fade = Math.min(.002, buffer.duration / 2);
  gain.gain.setValueAtTime(0,when); gain.gain.linearRampToValueAtTime(1,when+fade); gain.gain.setValueAtTime(1,when+buffer.duration-fade); gain.gain.linearRampToValueAtTime(0,when+buffer.duration);
  sources.add(source); source.onended = () => {sources.delete(source);source.disconnect();gain.disconnect();}; source.start(when); nextPlayback = when + buffer.duration; ensureWave(); status('Speaking · AI đang nói');
}
function stopAudio() { mutedUntilTurn = true; for (const source of sources) {try {source.stop();} catch {}} sources.clear(); nextPlayback = playback?.currentTime || 0; }
function showError(err) { status('Error · ' + err.message); $('settingsError').textContent = err.message; }
$('talk').addEventListener('pointerdown', e => {e.preventDefault(); $('talk').setPointerCapture(e.pointerId); startRecording();});
for (const event of ['pointerup','pointercancel','lostpointercapture']) $('talk').addEventListener(event, stopRecording);
window.addEventListener('blur', stopRecording); window.addEventListener('beforeunload', disconnect);
document.addEventListener('keydown', e => {if (e.code === 'Escape') stopAudio(); if (e.code === 'Space' && !e.repeat && (!$('settings').open && !$('memoryDialog').open) && (e.target===$('talk') || !['INPUT','TEXTAREA','SELECT','BUTTON'].includes(e.target.tagName))) {e.preventDefault();startRecording();}});
document.addEventListener('keyup', e => {if (e.code === 'Space') stopRecording();});
$('stopAudio').onclick = stopAudio; $('retry').onclick = connect;
$('settingsButton').onclick = async () => {if(profileId){const p=await api(`/api/profiles/${profileId}`);$('nickname').value=p.name;$('apiKey').placeholder=p.has_api_key?'Đã lưu an toàn · để trống để giữ key':'Nhập Gemini API key';}$('settings').showModal();}; $('closeSettings').onclick = () => {$('apiKey').value='';$('settings').close();};
$('showTranscript').onchange = () => $('transcript').hidden = !$('showTranscript').checked;
$('newConversation').onclick = () => newConversation().catch(showError);
$('profile').onchange = async () => {disconnect();profileId=$('profile').value;localStorage.setItem('companionProfile',profileId);const data=await loadHistory();if(data.conversations.length)await chooseConversation(data.active_conversation_id || data.conversations[0].id);else await newConversation();};
$('devices').onclick = async () => {let stream;try {stream=await navigator.mediaDevices.getUserMedia({audio:true});stream.getTracks().forEach(t=>t.stop());$('mic').replaceChildren();$('speaker').replaceChildren();option($('mic'),'','Micro mặc định');option($('speaker'),'','Loa mặc định của Windows');for(const d of await navigator.mediaDevices.enumerateDevices()){if(d.kind==='audioinput')option($('mic'),d.deviceId,d.label||'Micro');if(d.kind==='audiooutput')option($('speaker'),d.deviceId,d.label||'Loa');}}catch(err){showError(err);}finally{stream?.getTracks().forEach(t=>t.stop());}};
async function saveSettings(forceNew=false){
  try{
    const wasConnected=connected;disconnect();
    const fields={name:$('nickname').value,default_difficulty:$('difficulty').value,mic_device_id:$('mic').value,mic_label:$('mic').selectedOptions[0]?.textContent,speaker_device_id:$('speaker').value};
    if(playback){await playback.close();playback=null;playbackBus=null;nextPlayback=0;}
    if($('apiKey').value)fields.api_key=$('apiKey').value;
    if(!profileId||forceNew){const p=await api('/api/profiles','POST',fields);profileId=p.id;localStorage.setItem('companionProfile',p.id);option($('profile'),p.id,p.name);$('profile').value=p.id;conversationId='';await newConversation();}
    else {await api(`/api/profiles/${profileId}`,'PUT',fields);if(conversationId){await api(`${basePath()}/${conversationId}`,'PUT',{...selectedPolicy(),voice_name:$('voice').value,model_name:$('model').value,scenario:$('scenario').value});await chooseConversation(conversationId);}}
    if($('profile').selectedOptions[0])$('profile').selectedOptions[0].textContent=fields.name;
    $('apiKey').value='';$('settings').close();await loadHistory();if(wasConnected)connect();else status('Đã lưu · chọn Kết nối để kiểm tra Gemini.');
  }catch(err){showError(err);}
}
$('settingsForm').onsubmit=e=>{e.preventDefault();saveSettings();};$('createProfile').onclick=()=>{if($('settingsForm').reportValidity())saveSettings(true);};
$('mute').onchange=()=>{if($('mute').checked)stopAudio();};
$('review').onclick=()=>{if(!connected){status('Kết nối trước khi yêu cầu review.');return;}stopRecording();mutedUntilTurn=false;activeTranscript={};send({type:'review_request'});status('Thinking · Đang tổng kết từ hội thoại đã có.');};
$('previewVoice').onclick=()=>{if(!connected){status('Lưu giọng đã chọn và Kết nối trước khi thử giọng online.');return;}mutedUntilTurn=false;send({type:'voice_preview'});};
$('exportBackup').onclick=()=>{if(profileId){const a=document.createElement('a');a.href=`/api/profiles/${profileId}/export`;a.download='CompanionLite-backup.zip';a.click();}};
$('importBackup').onchange=async()=>{const file=$('importBackup').files[0];if(!file)return;if(!confirm('Nhập backup local? Profile trùng ID sẽ được khôi phục từ backup; bản hiện tại được lưu recovery mã hóa.'))return;try{disconnect();const form=new FormData();form.append('file',file);const response=await fetch('/api/profiles/import',{method:'POST',body:form});if(!response.ok)throw new Error('Không nhập được backup. Kiểm tra định dạng hoặc kích thước.');const data=await response.json();localStorage.setItem('companionProfile',data.profile.id);location.reload();}catch(err){showError(err);}finally{$('importBackup').value='';}};
$('eraseMemory').onclick=async()=>{if(!profileId||!confirm('Xóa TOÀN BỘ hội thoại, transcript, summary, từ mới và memory của profile này? Backup đã xuất là các bản riêng.'))return;try{disconnect();await api(`/api/profiles/${profileId}/memory`,'DELETE');conversationId='';$('transcript').replaceChildren();await loadHistory();status('Đã xóa memory · Micro đang tắt');}catch(err){showError(err);}};
async function showMemories(){
  const data=await api(`/api/profiles/${profileId}/memories`);$('memoryList').replaceChildren();
  for(const item of data.memories){const row=document.createElement('div');row.className='turn';const text=document.createElement('p');text.textContent=`${item.domain}: ${item.text}`;const edit=document.createElement('button');edit.textContent='Sửa';edit.onclick=()=>{editingMemoryId=item.id;$('memoryText').value=item.text;$('memoryDomain').value=item.domain;};const remove=document.createElement('button');remove.textContent='Xóa';remove.onclick=async()=>{disconnect();await api(`/api/profiles/${profileId}/memories/${item.id}`,'DELETE');await showMemories();};row.append(text,edit,remove);$('memoryList').append(row);}
  $('learningNotes').replaceChildren();if(conversationId){const notes=await api(`${basePath()}/${conversationId}/notes`);for(const item of notes.vocab_mistakes){const p=document.createElement('p');p.textContent=`${item.term}: ${item.note||''}`;$('learningNotes').append(p);}}
}
$('memoryButton').onclick=async()=>{if(!profileId)return;try{await showMemories();$('memoryDialog').showModal();}catch(err){showError(err);}};
$('closeMemory').onclick=()=>$('memoryDialog').close();
$('memoryForm').onsubmit=async e=>{e.preventDefault();if(!profileId)return;try{disconnect();await api(`/api/profiles/${profileId}/memories/${editingMemoryId||crypto.randomUUID()}`,'PUT',{domain:$('memoryDomain').value,text:$('memoryText').value});editingMemoryId=null;$('memoryText').value='';await showMemories();}catch(err){showError(err);}};
const wave = $('wave').getContext('2d');let waveFrame=0;
function ensureWave(){if(!waveFrame)waveFrame=requestAnimationFrame(drawWave);}
function drawWave() {waveFrame=0;const a=matchMedia('(prefers-reduced-motion: reduce)').matches?null:(micAnalyser || (sources.size ? playbackAnalyser : null));wave.clearRect(0,0,640,100);wave.strokeStyle='#176679';wave.lineWidth=2;wave.beginPath();const values=new Uint8Array(a?.frequencyBinCount || 128);if(a)a.getByteTimeDomainData(values);else values.fill(128);for(let i=0;i<values.length;i++){const x=i/(values.length-1)*640,y=50+(values[i]-128)*.35;i?wave.lineTo(x,y):wave.moveTo(x,y);}wave.stroke();if(a)waveFrame=requestAnimationFrame(drawWave);}drawWave();
async function init() {
  if(!('setSinkId' in AudioContext.prototype))$('speaker').disabled=true;
  const [voices, models, profiles, scenarios] = await Promise.all([api('/api/voices'),api('/api/models'),api('/api/profiles'),api('/api/scenarios')]);
  for(const s of scenarios.scenarios)option($('scenario'),s.id,s.label);
  for(const v of voices.voices)option($('voice'),v.name,`${v.name} · ${v.descriptor}`);$('voice').value=voices.default;
  for(const m of models.models)option($('model'),m.id,m.label);$('model').value=models.default;
  for(const p of profiles.profiles)option($('profile'),p.id,p.name);
  if(!profiles.profiles.some(p=>p.id===profileId))profileId=profiles.profiles[0]?.id || '';
  if(!profileId){$('settings').showModal();return;}$('profile').value=profileId;const data=await loadHistory();if(data.conversations.length)await chooseConversation(data.active_conversation_id||data.conversations[0].id);else await newConversation();
}
init().catch(showError);
