// Voice-only UI over the existing REST and Gemini relay protocol.
// PCM conversion, 16/24 kHz formats and edge fades follow upstream audio.js.
'use strict';
const $ = id => document.getElementById(id);
let profileId = localStorage.getItem('companionProfile') || '';
let conversationId = '', socket = null, retryTimer = null, connected = false;
let capture = null, recording = false, pendingPress = false, pressGeneration = 0;
let continuous = false, speechActive = false, voiceGate = null, playbackGeneration = 0;
let playback = null, playbackBus = null, nextPlayback = 0, sources = new Set();
let micAnalyser = null, playbackAnalyser = null, mutedUntilTurn = false;
let activeTranscript = {}, reconnectDelay = 2000;
let editingMemoryId = null;
let voiceProvider = 'gemini_live';
let responseStartedAt=0;
let lastMicMeter=0,micMeterEnergy=0,micMeterSamples=0;
function updateMicMeter(samples){for(const value of samples)micMeterEnergy+=value*value;micMeterSamples+=samples.length;const now=performance.now();if(now-lastMicMeter<100)return;lastMicMeter=now;const rms=Math.sqrt(micMeterEnergy/Math.max(1,micMeterSamples));micMeterEnergy=0;micMeterSamples=0;$('micLevel').value=Math.min(1,rms/.1);const db=rms>0?Math.max(-96,Math.round(20*Math.log10(rms))): -96;$('micLevelText').textContent=`Mức mic: ${db} dBFS · ${speechActive?'Đang gửi lời nói':rms>=Number($('sensitivity').value)?'Có tín hiệu':'Chưa bắt tiếng · thử mức Nhạy nếu nói nhỏ'}`;}
function selectedProvider(){return {voice_provider:$('voiceProvider').value,deepseek_model:$('deepseekModel').value,tts_model:$('ttsModel').value,transcription_model:'gemini-3.5-flash-lite'};}
function providerControls(){const hybrid=$('voiceProvider').value==='deepseek_gemini';$('deepseekSettings').hidden=!hybrid;$('model').disabled=hybrid;$('providerNotice').textContent=hybrid?'Gemini nhận âm thanh; DeepSeek nhận transcript và ngữ cảnh bạn cho phép; Gemini nhận lời đáp để đọc. Hai key lưu riêng bằng mã hóa Windows.':'Gemini Live gửi âm thanh và ngữ cảnh được cho phép đến Google.';}
$('voiceProvider').onchange=providerControls;
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
  voiceProvider=conv.config.voice_provider || 'gemini_live';$('voiceProvider').value=voiceProvider;$('deepseekModel').value=conv.config.deepseek_model || 'deepseek-flash';$('ttsModel').value=conv.config.tts_model || 'gemini-3.8-flash-lite-tts';providerControls();
  $('difficulty').value = conv.config.difficulty;
  $('mode').value = conv.config.mode || 'friend'; $('replyLanguage').value = conv.config.reply_language_preference || 'balanced';
  $('correction').value = conv.config.correction_intensity || 'gentle'; $('pace').value = conv.config.speech_pace || 'natural';
  $('humor').value=conv.config.humor_style || 'cheeky'; $('practice').value=conv.config.practice_style || 'natural';
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
  const conv = await api(basePath(), 'POST', {voice_name:$('voice').value, model_name:$('model').value, ...selectedPolicy(), ...selectedProvider(), scenario:$('scenario').value, native_language:'Vietnamese', target_language:'English'});
  await loadHistory(); await chooseConversation(conv.id);
}
function disconnect() {
  clearTimeout(retryTimer); connected = false; $('talk').disabled = true;
  stopRecording(); stopAudio();
  if (socket) { socket.manual = true; socket.close(); socket = null; }
}
function connect() {
  if (!conversationId) return;
  disconnect(); status(voiceProvider==='deepseek_gemini'?'Đang chuẩn bị DeepSeek + Gemini':'Đang kết nối đến Gemini');
  const route=voiceProvider==='deepseek_gemini'?'hybrid':'session';
  const s = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/${route}`); socket = s;
  let turnError=false;
  s.onopen = () => s.send(JSON.stringify({type:'init', profile_id:profileId, conversation_id:conversationId}));
  s.onmessage = event => {
    if (s !== socket) return;
    const msg = JSON.parse(event.data);
    if (msg.type === 'session_status') {
      if(recording || pendingPress)stopRecording();
      connected = !msg.unavailable; captureControls();
      if(msg.unavailable)s.manual=true;
      if (connected) { reconnectDelay = 2000; mutedUntilTurn=false; $('mode').value=msg.mode || 'friend'; policyControls(false); status('Listening · Sẵn sàng'); if(!$('transcript').childElementCount && !msg.resumed)send({type:'session_open'}); }
    } else if (msg.type === 'policy_pending') { stopRecording(); connected=false; captureControls(); status('Reconnecting · Đang đổi chế độ');
    } else if (msg.type === 'audio') { if (!mutedUntilTurn && !speechActive) playAudio(msg.data).catch(showError); }
    else if (msg.type === 'interrupted') { stopAudio(); mutedUntilTurn = false; delete activeTranscript.model; }
    else if (msg.type === 'quiz_resume') send({type:'quiz_skip',quiz_id:msg.quiz_id});
    else if (msg.type === 'transcript_in') addTranscript('user', msg.text, true);
    else if (msg.type === 'transcript_out') addTranscript('model', msg.text, true);
    else if (msg.type === 'turn_complete') { if(!speechActive){activeTranscript = {}; mutedUntilTurn = false; if(!turnError)status(continuous?'Listening · Micro đang bật, bạn cứ nói':'Listening · Sẵn sàng');} turnError=false;loadHistory().catch(showError); }
    else if (msg.type === 'error') { turnError=true;status('Error · ' + msg.message); }
    else if (msg.type === 'phase') {turnError=false;status(msg.message);}
    else if (msg.type === 'waiting_long') status(msg.active ? 'Thinking · Đang chờ Gemini' : 'Đã kết nối');
  };
  s.onerror = () => {stopRecording();status('Error · Không thể kết nối. Chọn Retry.');};
  s.onclose = () => {
    if (s !== socket || s.manual) return;
    connected = false; $('talk').disabled = true; policyControls(false); stopRecording(); stopAudio();
    status('Reconnecting · Chọn Retry để thử ngay');
    retryTimer = setTimeout(connect, reconnectDelay); reconnectDelay = Math.min(30000, reconnectDelay * 2);
  };
}
function send(msg) { if (socket?.readyState === WebSocket.OPEN && connected) socket.send(JSON.stringify(msg)); }
function selectedPolicy() { return {mode:$('mode').value,reply_language_preference:$('replyLanguage').value,correction_intensity:$('correction').value,difficulty:$('difficulty').value,speech_pace:$('pace').value,memory_policy:$('remember').checked?'allowed':'off',humor_style:$('humor').value,practice_style:$('practice').value}; }
function policyControls(disabled){for(const id of ['mode','replyLanguage','correction','pace','remember','humor','practice'])$(id).disabled=disabled;}
async function changePolicy() {
  if (!conversationId) return;
  if (!connected) {try{await api(`${basePath()}/${conversationId}`,'PUT',selectedPolicy());status('Đã lưu. Kết nối để bắt đầu.');}catch(err){showError(err);}return;}
  stopRecording();stopAudio();send({type:'policy_change',policy:selectedPolicy()});policyControls(true);status('Đang yêu cầu đổi chính sách...');
}
for(const id of ['mode','replyLanguage','correction','pace','remember','humor','practice'])$(id).addEventListener('change',changePolicy);
function encodePCM(samples) {
  const pcm = new Int16Array(samples.length);
  for (let i = 0; i < samples.length; i++) { const v = Math.max(-1, Math.min(1, samples[i])); pcm[i] = v < 0 ? v * 32768 : v * 32767; }
  const bytes = new Uint8Array(pcm.buffer); let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}
function captureControls(){
  $('talk').disabled=!connected || continuous;
  $('listen').disabled=!connected;
  $('listen').setAttribute('aria-pressed',String(continuous));
  $('listen').textContent=continuous?'Tắt mic': 'Bật nghe liên tục';
}
function beginSpeech(){
  responseStartedAt=0;$('responseTiming').textContent='';
  speechActive=true;stopAudio();mutedUntilTurn=false;activeTranscript={};send({type:'start_turn'});
  status('Listening · Đang nghe bạn');
}
function endSpeech(){
  if(!speechActive)return;
  speechActive=false;responseStartedAt=performance.now();send({type:'turn_complete'});status('Thinking · Đang chờ');
}
async function startRecording(handsFree=false) {
  if (pendingPress || recording || !connected) return;
  continuous=handsFree;captureControls();
  pendingPress = true; const generation = ++pressGeneration;
  let stream, ctx;
  try {
    stream = await navigator.mediaDevices.getUserMedia({audio: {deviceId: $('mic').value ? {exact:$('mic').value} : undefined, channelCount:1, echoCancellation:true, noiseSuppression:true, autoGainControl:true}});
    if (!pendingPress || generation !== pressGeneration || !connected) { stream.getTracks().forEach(t => t.stop()); return; }
    ctx = new AudioContext({sampleRate:16000}); await ctx.resume();
    await ctx.audioWorklet.addModule('/pcm-processor.js');
    if (!pendingPress || generation !== pressGeneration || !connected) { stream.getTracks().forEach(t=>t.stop()); await ctx.close(); return; }
    const worklet = new AudioWorkletNode(ctx, 'pcm-capture-processor');
    const input = ctx.createMediaStreamSource(stream); micAnalyser = ctx.createAnalyser();
    input.connect(micAnalyser); input.connect(worklet);
    const silent = ctx.createGain(); silent.gain.value = 0; worklet.connect(silent); silent.connect(ctx.destination);
    capture = {stream, ctx, worklet}; recording = true;
    $('micDevice').textContent='Đầu vào: '+(stream.getTracks()[0]?.label || $('mic').selectedOptions[0]?.textContent || 'Micro đã chọn');
    lastMicMeter=0;micMeterEnergy=0;micMeterSamples=0;
    for(const track of stream.getTracks())track.onended=()=>{stopRecording();status('Micro đã ngắt · bật lại khi sẵn sàng.');};
    ctx.onstatechange=()=>{if(ctx.state==='suspended' && capture?.ctx===ctx){stopRecording();status('Micro tạm dừng · bật lại khi sẵn sàng.');}};
    voiceGate=continuous?new LocalSpeechGate({sampleRate:ctx.sampleRate,threshold:Number($('sensitivity').value),silenceMs:Number($('responsePace').value)}):null;
    ensureWave();
    if(!continuous)beginSpeech();
    worklet.port.onmessage = event => {
      if(!recording || generation!==pressGeneration)return;
      updateMicMeter(event.data);
      if(!connected || socket?.bufferedAmount>524288){stopRecording();status('Micro đã tắt · kết nối chậm, chọn Retry.');return;}
      if(!continuous){send({type:'audio_chunk',data:encodePCM(event.data)});return;}
      const result=voiceGate.push(event.data,sources.size>0);
      if(result.start)beginSpeech();
      for(const samples of result.chunks)send({type:'audio_chunk',data:encodePCM(samples)});
      if(result.end)endSpeech();
      if(result.limit){stopRecording();status('Micro đã tắt sau lượt nói dài · bật lại để tiếp tục.');}
    };
    $('talk').classList.toggle('recording',!continuous); $('micStatus').textContent = continuous?'Micro đang bật · nghe liên tục':'Micro đang bật'; status('Listening · Đang nghe');
  } catch (err) {
    stream?.getTracks().forEach(t=>t.stop()); if (ctx && ctx.state !== 'closed') await ctx.close();
    if(generation!==pressGeneration)return;
    stopRecording();
    showError(new Error('Không mở được micro. Kiểm tra quyền micro trong Windows rồi thử lại.'));
  } finally { if (generation === pressGeneration) pendingPress = false; }
}
function stopRecording(reason='') {
  pendingPress = false; pressGeneration++;
  endSpeech();recording=false;continuous=false;voiceGate=null;
  if (capture) { capture.worklet.port.onmessage = null; capture.stream.getTracks().forEach(t=>t.stop()); capture.ctx.close().catch(()=>{}); capture = null; }
  micAnalyser = null; $('talk').classList.remove('recording'); $('micStatus').textContent = 'Micro đang tắt'+(typeof reason==='string' && reason?' · '+reason:'');
  $('micLevel').value=0;$('micLevelText').textContent='Mức mic: chưa thu âm';$('micDevice').textContent='';
  micMeterEnergy=0;micMeterSamples=0;
  captureControls();
}
async function playAudio(encoded) {
  const generation=playbackGeneration;
  if (!playback) {
    playback = new AudioContext({sampleRate:24000}); playbackBus = playback.createGain(); playbackAnalyser = playback.createAnalyser();
    playbackBus.connect(playbackAnalyser); playbackAnalyser.connect(playback.destination);
    if($('speaker').value){if(playback.setSinkId)await playback.setSinkId($('speaker').value);else status('WebView2 không hỗ trợ chọn loa riêng. Dùng cài đặt Windows.');}
  }
  await playback.resume(); if (generation!==playbackGeneration || speechActive || mutedUntilTurn || $('mute').checked) return;
  const bytes = Uint8Array.from(atob(encoded), c => c.charCodeAt(0)); const pcm = new Int16Array(bytes.buffer);
  const buffer = playback.createBuffer(1, pcm.length, 24000); const floats = buffer.getChannelData(0);
  for (let i = 0; i < pcm.length; i++) floats[i] = pcm[i] / 32768;
  const source = playback.createBufferSource(); source.buffer = buffer; const gain = playback.createGain(); source.connect(gain); gain.connect(playbackBus);
  const when = Math.max(nextPlayback, playback.currentTime), fade = Math.min(.002, buffer.duration / 2);
  gain.gain.setValueAtTime(0,when); gain.gain.linearRampToValueAtTime(1,when+fade); gain.gain.setValueAtTime(1,when+buffer.duration-fade); gain.gain.linearRampToValueAtTime(0,when+buffer.duration);
  sources.add(source); source.onended = () => {sources.delete(source);source.disconnect();gain.disconnect();}; source.start(when); nextPlayback = when + buffer.duration; ensureWave(); status('Speaking · AI đang nói');
  if(responseStartedAt){const seconds=(performance.now()-responseStartedAt)/1000+Math.max(0,when-playback.currentTime);$('responseTiming').textContent=`Giọng trả lời sau ${seconds.toFixed(1)} giây`;responseStartedAt=0;}
}
function stopAudio() { playbackGeneration++;responseStartedAt=0;mutedUntilTurn = true; for (const source of sources) {try {source.stop();} catch {}} sources.clear(); nextPlayback = playback?.currentTime || 0; }
function showError(err) { status('Error · ' + err.message); $('settingsError').textContent = err.message; }
$('talk').addEventListener('pointerdown', e => {e.preventDefault(); $('talk').setPointerCapture(e.pointerId); startRecording();});
for (const event of ['pointerup','pointercancel','lostpointercapture']) $('talk').addEventListener(event,()=>{if(!continuous)stopRecording();});
$('listen').onclick=()=>{if(continuous || pendingPress)stopRecording();else{stopRecording();startRecording(true);}};
$('sensitivity').onchange=()=>{if(voiceGate)voiceGate.threshold=Number($('sensitivity').value);};
$('responsePace').onchange=()=>{localStorage.setItem('companionResponsePause',$('responsePace').value);if(voiceGate)voiceGate.silenceMs=Number($('responsePace').value);};
const savedResponsePace=localStorage.getItem('companionResponsePause');if(['600','800','1200'].includes(savedResponsePace))$('responsePace').value=savedResponsePace;
window.addEventListener('blur',()=>stopRecording('Bạn vừa chuyển cửa sổ; bấm Bật nghe liên tục để nghe lại')); window.addEventListener('beforeunload', disconnect);
document.addEventListener('keydown', e => {if (e.code === 'Escape') {stopRecording();stopAudio();} if (e.code === 'Space' && !continuous && !e.repeat && (!$('settings').open && !$('memoryDialog').open) && (e.target===$('talk') || !['INPUT','TEXTAREA','SELECT','BUTTON'].includes(e.target.tagName))) {e.preventDefault();startRecording();}});
document.addEventListener('keyup', e => {if (e.code === 'Space' && !continuous) stopRecording();});
$('stopAudio').onclick = stopAudio; $('retry').onclick = connect;
$('settingsButton').onclick = async () => {stopRecording();if(profileId){const p=await api(`/api/profiles/${profileId}`);$('nickname').value=p.name;$('apiKey').placeholder=p.has_api_key?'Đã lưu an toàn · để trống để giữ key':'Nhập Gemini API key';$('deepseekKey').placeholder=p.has_deepseek_api_key?'Đã lưu an toàn · để trống để giữ key':'Nhập DeepSeek API key';}providerControls();$('settings').showModal();}; $('closeSettings').onclick = () => {$('apiKey').value='';$('deepseekKey').value='';$('settings').close();};
$('settings').addEventListener('close',()=>{$('apiKey').value='';$('deepseekKey').value='';});
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
    if($('deepseekKey').value)fields.deepseek_api_key=$('deepseekKey').value;
    if(!profileId||forceNew){const p=await api('/api/profiles','POST',fields);profileId=p.id;localStorage.setItem('companionProfile',p.id);option($('profile'),p.id,p.name);$('profile').value=p.id;conversationId='';await newConversation();}
    else {await api(`/api/profiles/${profileId}`,'PUT',fields);if(conversationId){await api(`${basePath()}/${conversationId}`,'PUT',{...selectedPolicy(),...selectedProvider(),voice_name:$('voice').value,model_name:$('model').value,scenario:$('scenario').value});await chooseConversation(conversationId);}}
    if($('profile').selectedOptions[0])$('profile').selectedOptions[0].textContent=fields.name;
    $('apiKey').value='';$('deepseekKey').value='';$('settings').close();await loadHistory();if(wasConnected)connect();else status('Đã lưu · chọn Kết nối để bắt đầu.');
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
$('memoryButton').onclick=async()=>{stopRecording();if(!profileId)return;try{await showMemories();$('memoryDialog').showModal();}catch(err){showError(err);}};
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
