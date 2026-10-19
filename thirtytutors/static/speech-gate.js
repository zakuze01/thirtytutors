// Energy-based local turn detection, not speaker recognition or transcription.
// Keeps only a bounded in-memory pre-roll; the relay still uses Gemini audio.
(function(root) {
  'use strict';
  class LocalSpeechGate {
    constructor({sampleRate=16000, threshold=.007, attackMs=120, silenceMs=800, preRollMs=320, maxTurnMs=30000}={}) {
      Object.assign(this,{sampleRate,threshold,attackMs,silenceMs,preRollMs,maxTurnMs});
      this.active=false;this.candidate=0;this.onset=[];this.onsetMs=0;this.silence=0;this.elapsed=0;this.pre=[];this.preSamples=0;
    }
    push(samples, aiSpeaking=false) {
      const ms=samples.length/this.sampleRate*1000;
      let energy=0;for(const v of samples)energy+=v*v;
      const rms=Math.sqrt(energy/Math.max(1,samples.length));
      const voiced=rms >= this.threshold*(aiSpeaking?1.6:1);
      if(!this.active){
        this.pre.push(samples);this.preSamples+=samples.length;
        while(this.pre.length>1 && this.preSamples-this.pre[0].length>=this.sampleRate*this.preRollMs/1000)this.preSamples-=this.pre.shift().length;
        // Real syllables include brief unvoiced gaps. Count speech in a bounded
        // rolling window rather than demanding 120 ms of uninterrupted energy.
        this.onset.push({ms,voiced});this.onsetMs+=ms;if(voiced)this.candidate+=ms;
        while(this.onsetMs>this.attackMs*2){const first=this.onset[0];const trim=Math.min(first.ms,this.onsetMs-this.attackMs*2);first.ms-=trim;this.onsetMs-=trim;if(first.voiced)this.candidate-=trim;if(first.ms<=0)this.onset.shift();}
        if(!voiced || this.candidate<this.attackMs)return {start:false,end:false,chunks:[]};
        this.active=true;this.elapsed=this.preSamples/this.sampleRate*1000;this.silence=0;this.candidate=0;this.onset=[];this.onsetMs=0;
        const chunks=this.pre;this.pre=[];this.preSamples=0;
        return {start:true,end:false,chunks};
      }
      this.elapsed+=ms;this.silence=rms>=this.threshold*.6?0:this.silence+ms;
      const limit=this.elapsed>=this.maxTurnMs;
      const end=limit || this.silence>=this.silenceMs;
      if(end){this.active=false;this.candidate=0;this.silence=0;}
      return {start:false,end,chunks:[samples],limit};
    }
  }
  if(typeof module!=='undefined' && module.exports)module.exports=LocalSpeechGate;
  else root.LocalSpeechGate=LocalSpeechGate;
})(globalThis);
