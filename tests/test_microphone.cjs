const test=require('node:test');
const assert=require('node:assert/strict');
const mic=require('../thirtytutors/static/microphone.js');
const error=name=>Object.assign(new Error('private provider details'),{name});
const device=(id,label='Realtek')=>({kind:'audioinput',deviceId:id,label});
function stream(){const track={stopped:false,stop(){this.stopped=true;}};return {track,getTracks:()=>[track]};}
function fake(sequence,devices=[]){const calls=[];return {calls,async getUserMedia(opts){calls.push(opts);const next=sequence.shift();if(next instanceof Error)throw next;return typeof next==='function'?next():next;},async enumerateDevices(){return devices;}};}

test('default and valid explicit device open once without enumeration',async()=>{
  for(const id of ['', 'current']){const s=stream(),media=fake([s]);assert.equal(await mic.open(media,id,'Realtek'),s);assert.equal(media.calls.length,1);assert.equal(media.calls[0].audio.deviceId?.exact,id||undefined);assert.equal(s.track.stopped,false);}
});
test('stale origin ID is rebound to the same unique label; probe is stopped',async()=>{
  for(const name of ['OverconstrainedError','NotFoundError']){
    const probe=stream(),chosen=stream();const media=fake([error(name),probe,chosen],[device('new'),device('gs3','GS3')]);
    assert.equal(await mic.open(media,'old','Realtek'),chosen);assert(probe.track.stopped);
    assert.equal(media.calls[1].audio,true);assert.equal(media.calls[2].audio.deviceId.exact,'new');
  }
});
test('missing or ambiguous saved mic never falls back to another input',async()=>{
  for(const devices of [[device('gs3','GS3')],[device('a'),device('b')]]){
    const probe=stream(),media=fake([error('OverconstrainedError'),probe],devices);
    await assert.rejects(mic.open(media,'old','Realtek'),{name:'SavedMicrophoneUnavailable'});
    assert(probe.track.stopped);assert.equal(media.calls.length,2);
  }
});
test('denied, busy and unrelated errors are not retried',async()=>{
  for(const name of ['NotAllowedError','NotReadableError','SecurityError','TypeError']){
    const media=fake([error(name)]);await assert.rejects(mic.open(media,'old','Realtek'),{name});assert.equal(media.calls.length,1);
    assert(!mic.errorMessage(error(name)).includes('private provider details'));
  }
});
test('cancel before request makes no microphone calls',async()=>{
  const media=fake([]);await assert.rejects(mic.open(media,'old','Realtek',()=>false),{name:'AbortError'});assert.equal(media.calls.length,0);
});
test('late initial permission result is stopped after cancellation',async()=>{
  let current=true;const s=stream(),media=fake([()=>{current=false;return s;}]);
  await assert.rejects(mic.open(media,'current','Realtek',()=>current),{name:'AbortError'});assert(s.track.stopped);
});
test('cancel while permission probe is pending never opens final capture',async()=>{
  let current=true;const probe=stream(),media=fake([error('OverconstrainedError'),()=>{current=false;return probe;}],[device('new')]);
  await assert.rejects(mic.open(media,'old','Realtek',()=>current),{name:'AbortError'});assert(probe.track.stopped);assert.equal(media.calls.length,2);
});
test('cancel while enumeration is pending never opens final capture',async()=>{
  let current=true;const probe=stream(),media=fake([error('OverconstrainedError'),probe]);media.enumerateDevices=async()=>{current=false;return [device('new')];};
  await assert.rejects(mic.open(media,'old','Realtek',()=>current),{name:'AbortError'});assert(probe.track.stopped);assert.equal(media.calls.length,2);
});
test('late final stream is stopped after cancellation',async()=>{
  let current=true;const probe=stream(),chosen=stream(),media=fake([error('OverconstrainedError'),probe,()=>{current=false;return chosen;}],[device('new')]);
  await assert.rejects(mic.open(media,'old','Realtek',()=>current),{name:'AbortError'});assert(probe.track.stopped);assert(chosen.track.stopped);
});
test('device matching uses IDs first and ignores output devices',()=>{
  assert.equal(mic.match([device('id','Changed label')],'id','Realtek').deviceId,'id');
  assert.equal(mic.match([{kind:'audiooutput',deviceId:'id',label:'Realtek'}],'id','Realtek'),null);
});
