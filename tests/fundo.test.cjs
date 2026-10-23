const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');

function ambiente(entrada=false){
  const eventos={},frames=new Map(),elipses=[];let id=0,desenhos=0;
  const classes=new Set(entrada?['perfil-avatar-entrada']:[]);
  const root={dataset:{movimento:'on'},classList:{contains:c=>classes.has(c)}};
  const gradiente={addColorStop(){}};
  const ctx=new Proxy({},{get:(_,k)=>k.startsWith('create')?()=>gradiente:(...args)=>{assert.ok(!args.some(n=>typeof n==='number'&&!Number.isFinite(n)));if(k==='ellipse')elipses.push(args);desenhos++;},set:()=>true});
  const canvas={dataset:{efeito:'energia-perfil'},parentElement:{getBoundingClientRect:()=>({width:1440,height:900})},style:{},getContext:()=>ctx};
  const ouvir=(nome,fn)=>(eventos[nome]??=[]).push(fn);
  const document={documentElement:root,hidden:false,readyState:'complete',querySelectorAll:()=>[canvas],addEventListener:ouvir};
  const window={devicePixelRatio:1,matchMedia:()=>({matches:false}),addEventListener:ouvir};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/spectra_link_guard/web/static/fundo.js'),'utf8'),{window,document,Math,getComputedStyle:()=>({getPropertyValue:()=> '17 142 148'}),requestAnimationFrame:cb=>{frames.set(++id,cb);return id;},cancelAnimationFrame:i=>frames.delete(i),ResizeObserver:class{constructor(cb){this.cb=cb;}observe(){this.cb();}},IntersectionObserver:class{constructor(cb){this.cb=cb;}observe(){this.cb([{isIntersecting:true}]);}}});
  return {root,document,classes,frames,posicoes:()=>elipses.slice(-8),emitir:n=>(eventos[n]||[]).forEach(fn=>fn()),quadro:t=>{const lista=[...frames.values()];frames.clear();lista.forEach(cb=>cb(t));return desenhos;}};
}

test('fundo pausa durante o deslocamento e retoma ao terminar',()=>{
  const a=ambiente();assert.equal(a.frames.size,1);const antes=a.quadro(100);
  a.root.dataset.perfilTransicao='deslocando';a.emitir('spectra:perfil-transicao');
  assert.equal(a.frames.size,0);assert.equal(a.quadro(200),antes);
  delete a.root.dataset.perfilTransicao;a.emitir('spectra:perfil-transicao');
  assert.equal(a.frames.size,1);assert.ok(a.quadro(300)>antes);
});

test('aguardar a foto não inicia o fundo antes da animação do avatar',()=>{
  const a=ambiente(true);assert.equal(a.frames.size,0);
  a.classes.clear();a.root.dataset.perfilTransicao='deslocando';a.emitir('spectra:perfil-transicao');assert.equal(a.frames.size,0);
  delete a.root.dataset.perfilTransicao;a.emitir('spectra:perfil-transicao');assert.equal(a.frames.size,1);
});

test('terminar o voo não reativa animações quando a aba está oculta',()=>{
  const a=ambiente();a.document.hidden=true;a.emitir('visibilitychange');
  a.emitir('spectra:perfil-transicao');assert.equal(a.frames.size,0);
  a.document.hidden=false;a.emitir('visibilitychange');assert.equal(a.frames.size,1);
});

test('o fundo já está desenhado na entrada e retoma sem saltar de posição',()=>{
  const a=ambiente(true),primeiraPintura=a.posicoes();
  assert.equal(primeiraPintura.length,8);
  a.classes.clear();a.emitir('spectra:perfil-transicao');a.quadro(5000);
  assert.deepEqual(a.posicoes(),primeiraPintura);
  a.quadro(5100);const antesDaPausa=a.posicoes();
  assert.notDeepEqual(antesDaPausa,primeiraPintura);
  a.root.dataset.perfilTransicao='deslocando';a.emitir('spectra:perfil-transicao');
  delete a.root.dataset.perfilTransicao;a.emitir('spectra:perfil-transicao');a.quadro(20000);
  assert.deepEqual(a.posicoes(),antesDaPausa);
});
