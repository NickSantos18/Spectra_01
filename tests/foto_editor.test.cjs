const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../src/spectra_link_guard/web/static/foto-editor.js'), 'utf8');

function ambiente() {
  const desenhos = [];
  let fechadas = 0, exportadas = 0;
  class Elemento extends EventTarget {
    constructor(){super();this.value='1';this.width=512;this.height=512;this.classList={add(){},remove(){}};}
    getContext(){return {clearRect(){},drawImage(...args){desenhos.push(args);}};}
    getBoundingClientRect(){return {width:320,height:320};}
    hasPointerCapture(){return false;}
    setPointerCapture(){}
    focus(){}
    showModal(){this.aberto=true;}
    close(){this.aberto=false;this.dispatchEvent(new Event('close'));}
    toDataURL(){exportadas++;return 'data:image/png;base64,recorte';}
  }
  const nodes = new Map();
  const document={getElementById:id=>{if(!nodes.has(id))nodes.set(id,new Elemento());return nodes.get(id);},createElement:()=>new Elemento()};
  const window={};
  vm.runInNewContext(source,{window,document,fetch:async()=>({blob:async()=>({type:'image/png',size:100})}),createImageBitmap:async()=>({width:1200,height:800,close(){fechadas++;}})});
  const evento=(id,tipo,props={})=>{const e=new Event(tipo,{cancelable:true});Object.assign(e,props);document.getElementById(id).dispatchEvent(e);};
  return {editor:window.SpectraFoto,document,desenhos,evento,estado:()=>({fechadas,exportadas})};
}

test('recorte preenche o círculo em fotos horizontais e verticais, em qualquer limite',()=>{
  const {editor}=ambiente();
  for(const [w,h] of [[1200,800],[600,1600],[256,256]]){
    for(const zoom of [0,1,1.5,4,10])for(const [x,y] of [[-999,-999],[w/2,h/2],[w+999,h+999]]){
      const r=editor.calcularRecorte(w,h,zoom,x,y);
      assert.ok(r.x>=0&&r.y>=0);
      assert.ok(r.x+r.lado<=w+1e-8&&r.y+r.lado<=h+1e-8);
      assert.ok(r.lado<=Math.min(w,h)&&r.lado>=Math.min(w,h)/4);
    }
  }
});

test('zoom, arraste e teclado afetam o recorte exportado em 256 pixels',async()=>{
  const a=ambiente();
  const pending=a.editor.abrir({type:'image/png',size:100});await new Promise(setImmediate);
  a.document.getElementById('recorte-zoom').value='2';a.evento('recorte-zoom','input');
  a.evento('recorte-canvas','pointerdown',{isPrimary:true,button:0,pointerId:1,clientX:100,clientY:100});
  a.evento('recorte-canvas','pointermove',{pointerId:1,clientX:180,clientY:140});
  a.evento('recorte-canvas','pointerup');
  a.evento('recorte-canvas','keydown',{key:'ArrowRight',shiftKey:false});
  a.evento('recorte-aplicar','click');
  assert.equal(await pending,'data:image/png;base64,recorte');
  const args=a.desenhos.at(-1);
  assert.ok(args[1]<400&&args[2]<200);
  assert.deepEqual(args.slice(3),[400,400,0,0,256,256]);
  assert.deepEqual(a.estado(),{fechadas:1,exportadas:1});
});

test('cancelar não exporta foto; reabrir e centralizar não duplicam eventos',async()=>{
  const a=ambiente();
  let pending=a.editor.abrir({type:'image/png',size:100});await new Promise(setImmediate);
  a.evento('recorte-cancelar','click');assert.equal(await pending,null);
  assert.equal(a.estado().exportadas,0);
  pending=a.editor.abrir({type:'image/png',size:100});await new Promise(setImmediate);
  a.document.getElementById('recorte-zoom').value='4';a.evento('recorte-zoom','input');
  a.evento('recorte-redefinir','click');a.evento('recorte-aplicar','click');
  await pending;
  assert.deepEqual(a.desenhos.at(-1).slice(1),[200,0,800,800,0,0,256,256]);
  assert.deepEqual(a.estado(),{fechadas:2,exportadas:1});
});

test('rejeita arquivo inválido ou acima do limite antes de abrir o editor',async()=>{
  const a=ambiente();
  await assert.rejects(a.editor.abrir({type:'text/plain',size:100}));
  await assert.rejects(a.editor.abrir({type:'image/png',size:9*1024*1024}));
  assert.equal(a.estado().exportadas,0);
});

test('posição horizontal e vertical escolhidas são mantidas ao reabrir a mesma imagem',async()=>{
  const a=ambiente(), imagem={type:'image/png',size:100};
  let pending=a.editor.abrir(imagem);await new Promise(setImmediate);
  a.document.getElementById('recorte-zoom').value='2';a.evento('recorte-zoom','input');
  a.document.getElementById('recorte-horizontal').value='100';a.evento('recorte-horizontal','input');
  a.document.getElementById('recorte-vertical').value='0';a.evento('recorte-vertical','input');
  a.evento('recorte-aplicar','click');await pending;
  assert.deepEqual(a.desenhos.at(-1).slice(1),[800,0,400,400,0,0,256,256]);
  pending=a.editor.abrir(imagem);await new Promise(setImmediate);
  assert.equal(a.document.getElementById('recorte-zoom').value,'2');
  assert.equal(a.document.getElementById('recorte-horizontal').value,'100');
  assert.equal(a.document.getElementById('recorte-vertical').value,'0');
  a.evento('recorte-cancelar','click');await pending;
});
