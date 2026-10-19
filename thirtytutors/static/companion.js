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
    b.onclick = () => chooseConversation(conv.id).catch(showError); $('history').append(b);
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
  $('mode').value = conv.config.mode || 'friend'; $('replyLanguage').value = conv.config.reply_language_preference || 'english_first';
  $('correction').value = conv.config.correction_intensity || 'gentle'; $('pace').value = conv.config.speech_pace || 'natural';
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
      if (connected) { reconnectDelay = 2000; mutedUntilTurn=false; $('mode').value=msg.mode || 'friend'; $('mode').disabled=false; status('Listening · Sẵn sàng'); }
    } else if (msg.type === 'policy_pending') { connected=false; $('talk').disabled=true; status('Reconnecting · Đang đổi chế độ');
    } else if (msg.type === 'audio') { if (!mutedUntilTurn) playAudio(msg.data).catch(showError); }
    else if (msg.type === 'interrupted') { stopAudio(); mutedUntilTurn = false; }
    else if (msg.type === 'transcript_in') addTranscript('user', msg.text, true);
    else if (msg.type === 'transcript_out') addTranscript('model', msg.text, true);
    else if (msg.type === 'turn_complete') { activeTranscript = {}; mutedUntilTurn = false; status('Listening · Sẵn sàng'); loadHistory().catch(showError); }
    else if (msg.type === 'error') { status('Error · ' + msg.message); }
    else if (msg.type === 'waiting_long') status(msg.active ? 'Thinking · Đang chờ Gemini' : 'Đã kết nối');
  };
  s.onerror = () => status('Error · Không thể kết nối. Chọn Retry.');
  s.onclose = () => {
    if (s !== socket || s.manual) return;
    connected = false; $('talk').disabled = true; stopRecording(); stopAudio();
    status('Reconnecting · Chọn Retry để thử ngay');
    retryTimer = setTimeout(connect, reconnectDelay); reconnectDelay = Math.min(30000, reconnectDelay * 2);
  };
}
function send(msg) { if (socket?.readyState === WebSocket.OPEN && connected) socket.send(JSON.stringify(msg)); }
function selectedPolicy() { return {mode:$('mode').value,reply_language_preference:$('replyLanguage').value,correction_intensity:$('correction').value,difficulty:$('difficulty').value,speech_pace:$('pace').value}; }
function changePolicy() {
  if (!connected) {status('Kết nối trước khi áp dụng thay đổi cho hội thoại hiện tại.'); return;}
  stopRecording();stopAudio();send({type:'policy_change',policy:selectedPolicy()});$('mode').disabled=true;status('Đang yêu cầu đổi chính sách...');
}
for(const id of ['mode','replyLanguage','correction','pace'])$(id).addEventListener('change',changePolicy);
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
  }
  await playback.resume(); if (mutedUntilTurn) return;
  const bytes = Uint8Array.from(atob(encoded), c => c.charCodeAt(0)); const pcm = new Int16Array(bytes.buffer);
  const buffer = playback.createBuffer(1, pcm.length, 24000); const floats = buffer.getChannelData(0);
  for (let i = 0; i < pcm.length; i++) floats[i] = pcm[i] / 32768;
  const source = playback.createBufferSource(); source.buffer = buffer; const gain = playback.createGain(); source.connect(gain); gain.connect(playbackBus);
  const when = Math.max(nextPlayback, playback.currentTime), fade = Math.min(.002, buffer.duration / 2);
  gain.gain.setValueAtTime(0,when); gain.gain.linearRampToValueAtTime(1,when+fade); gain.gain.setValueAtTime(1,when+buffer.duration-fade); gain.gain.linearRampToValueAtTime(0,when+buffer.duration);
  sources.add(source); source.onended = () => {sources.delete(source);source.disconnect();gain.disconnect();}; source.start(when); nextPlayback = when + buffer.duration; status('Speaking · AI đang nói');
}
function stopAudio() { mutedUntilTurn = true; for (const source of sources) {try {source.stop();} catch {}} sources.clear(); nextPlayback = playback?.currentTime || 0; }
function showError(err) { status('Error · ' + err.message); $('settingsError').textContent = err.message; }
$('talk').addEventListener('pointerdown', e => {e.preventDefault(); $('talk').setPointerCapture(e.pointerId); startRecording();});
for (const event of ['pointerup','pointercancel','lostpointercapture']) $('talk').addEventListener(event, stopRecording);
window.addEventListener('blur', stopRecording); window.addEventListener('beforeunload', disconnect);
document.addEventListener('keydown', e => {if (e.code === 'Escape') stopAudio(); if (e.code === 'Space' && !e.repeat && !['INPUT','TEXTAREA','SELECT','BUTTON'].includes(e.target.tagName)) {e.preventDefault();startRecording();}});
document.addEventListener('keyup', e => {if (e.code === 'Space') stopRecording();});
$('stopAudio').onclick = stopAudio; $('retry').onclick = connect;
$('settingsButton').onclick = () => $('settings').showModal(); $('closeSettings').onclick = () => $('settings').close();
$('showTranscript').onchange = () => $('transcript').hidden = !$('showTranscript').checked;
$('newConversation').onclick = () => newConversation().catch(showError);
$('profile').onchange = async () => {disconnect();profileId=$('profile').value;localStorage.setItem('companionProfile',profileId);const data=await loadHistory();if(data.conversations.length)await chooseConversation(data.active_conversation_id || data.conversations[0].id);else await newConversation();};
$('devices').onclick = async () => {let stream;try {stream=await navigator.mediaDevices.getUserMedia({audio:true});stream.getTracks().forEach(t=>t.stop());$('mic').replaceChildren();option($('mic'),'','Micro mặc định');for(const d of await navigator.mediaDevices.enumerateDevices())if(d.kind==='audioinput')option($('mic'),d.deviceId,d.label||'Micro');}catch(err){showError(err);}finally{stream?.getTracks().forEach(t=>t.stop());}};
$('settingsForm').onsubmit = async e => {e.preventDefault();try {const p=await api('/api/profiles','POST',{name:$('nickname').value,api_key:$('apiKey').value,native_language:'Vietnamese'});$('apiKey').value='';profileId=p.id;localStorage.setItem('companionProfile',p.id);option($('profile'),p.id,p.name);$('profile').value=p.id;await newConversation();$('settings').close();}catch(err){showError(err);}};
const wave = $('wave').getContext('2d');
function drawWave() {const a=micAnalyser || (sources.size ? playbackAnalyser : null);wave.clearRect(0,0,640,100);wave.strokeStyle='#176679';wave.lineWidth=2;wave.beginPath();const values=new Uint8Array(a?.frequencyBinCount || 128);if(a)a.getByteTimeDomainData(values);else values.fill(128);for(let i=0;i<values.length;i++){const x=i/(values.length-1)*640,y=50+(values[i]-128)*.35;i?wave.lineTo(x,y):wave.moveTo(x,y);}wave.stroke();requestAnimationFrame(drawWave);}drawWave();
async function init() {
  const [voices, models, profiles, scenarios] = await Promise.all([api('/api/voices'),api('/api/models'),api('/api/profiles'),api('/api/scenarios')]);
  for(const s of scenarios.scenarios)option($('scenario'),s.id,s.label);
  for(const v of voices.voices)option($('voice'),v.name,`${v.name} · ${v.descriptor}`);$('voice').value=voices.default;
  for(const m of models.models)option($('model'),m.id,m.label);$('model').value=models.default;
  for(const p of profiles.profiles)option($('profile'),p.id,p.name);
  if(!profiles.profiles.some(p=>p.id===profileId))profileId=profiles.profiles[0]?.id || '';
  if(!profileId){$('settings').showModal();return;}$('profile').value=profileId;const data=await loadHistory();if(data.conversations.length)await chooseConversation(data.active_conversation_id||data.conversations[0].id);else await newConversation();
}
init().catch(showError);
