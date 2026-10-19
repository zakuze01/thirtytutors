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
  const gate=new Gate();
  assert(feed(gate,400,.018,true).every(e=>!e.start));
  assert.equal(feed(gate,200,.08,true).filter(e=>e.start).length,1);
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
