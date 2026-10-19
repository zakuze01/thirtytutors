// Deterministic PCM boundaries, not a claim about real microphone/echo quality.
const test=require('node:test');
const assert=require('node:assert/strict');
const Gate=require('../thirtytutors/static/speech-gate.js');
function feed(gate,ms,amplitude=0,speaking=false,size=128){
  const events=[];
  for(let n=0;n<ms*16;n+=size)events.push(gate.push(new Float32Array(size).fill(amplitude),speaking));
  return events;
}
test('idle and short click send no turn; pre-roll remains bounded',()=>{
  const gate=new Gate();
  assert(feed(gate,10000).every(e=>!e.start && !e.end && !e.chunks.length));
  assert(feed(gate,32,.1).every(e=>!e.start));
  feed(gate,1000);
  assert(gate.preSamples<=5120+128);
});
test('speech includes pre-roll and survives a natural short pause',()=>{
  const gate=new Gate();feed(gate,400);
  const starts=feed(gate,240,.08).filter(e=>e.start);
  assert.equal(starts.length,1);
  assert(starts[0].chunks.some(c=>c[0]===0));
  assert(starts[0].chunks.some(c=>c[0]>.07));
  assert(feed(gate,400).every(e=>!e.end));
  assert(feed(gate,240,.08).every(e=>!e.start && !e.end));
  assert.equal(feed(gate,900).filter(e=>e.end).length,1);
  assert.equal(feed(gate,200,.08).filter(e=>e.start).length,1);
});
test('playback raises threshold but louder barge-in is accepted',()=>{
  const gate=new Gate({threshold:.014});
  assert(feed(gate,400,.018,true).every(e=>!e.start));
  assert.equal(feed(gate,200,.08,true).filter(e=>e.start).length,1);
});
test('syllables with short unvoiced gaps still start a turn',()=>{
  const gate=new Gate({threshold:.014});const events=[];
  // 64 ms voice, 32 ms unvoiced, repeated: no continuous 120 ms segment.
  for(let i=0;i<3;i++){events.push(...feed(gate,64,.025));events.push(...feed(gate,32,0));}
  assert.equal(events.filter(e=>e.start).length,1);
  assert.equal(feed(gate,900).filter(e=>e.end).length,1);
});
test('widely spaced clicks never accumulate into a speech turn',()=>{
  const gate=new Gate();let starts=0;
  for(let i=0;i<100;i++){starts+=feed(gate,16,.1).filter(e=>e.start).length;starts+=feed(gate,120).filter(e=>e.start).length;}
  assert.equal(starts,0);assert(gate.onsetMs<=240);
});
test('new default admits a quiet signal previously below the threshold',()=>{
  const quiet=feed(new Gate(),200,.009);
  assert.equal(quiet.filter(e=>e.start).length,1);
  assert(feed(new Gate({threshold:.014}),200,.009).every(e=>!e.start));
});
test('short syllable dips do not split an active turn',()=>{
  const gate=new Gate();feed(gate,200,.02);
  // Below start threshold, above the release threshold.
  assert(feed(gate,1000,.005).every(e=>!e.end));
  assert.equal(feed(gate,900).filter(e=>e.end).length,1);
});
test('continuous sound has a bounded maximum turn',()=>{
  const gate=new Gate({maxTurnMs:1000});
  const events=feed(gate,1000,.1);
  assert.equal(events.filter(e=>e.limit && e.end).length,1);
  assert.equal(gate.active,false);
});
test('turn boundaries use PCM duration, independent of packet size',()=>{
  for(const size of [128,256,512]){
    const gate=new Gate();
    assert.equal(feed(gate,300,.08,false,size).filter(e=>e.start).length,1);
    assert.equal(feed(gate,900,0,false,size).filter(e=>e.end).length,1);
  }
});
