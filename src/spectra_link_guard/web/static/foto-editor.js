/* Recorte local: só o PNG aplicado é enviado quando o perfil é salvo. */
(() => {
  function calcularRecorte(largura, altura, zoom, centroX=largura/2, centroY=altura/2) {
    const lado=Math.min(largura,altura)/Math.max(1,Math.min(4,zoom));
    const x=Math.max(0,Math.min(largura-lado,centroX-lado/2));
    const y=Math.max(0,Math.min(altura-lado,centroY-lado/2));
    return {x,y,lado,centroX:x+lado/2,centroY:y+lado/2};
  }

  let ocupado=false;
  let ultimoAjuste=null;
  async function abrir(origem) {
    if(ocupado)return null;
    ocupado=true;
    let bitmap;
    try {
      const blob=typeof origem==='string' ? await (await fetch(origem)).blob() : origem;
      if(!blob||!blob.type.startsWith('image/')||blob.size>8*1024*1024)throw Error('Escolha uma imagem de até 8 MB.');
      try {bitmap=await createImageBitmap(blob);}catch{throw Error('Não foi possível abrir esta imagem. Escolha outra foto.');}
      const modal=document.getElementById('editor-foto');
      const canvas=document.getElementById('recorte-canvas');
      const ctx=canvas.getContext('2d');
      const slider=document.getElementById('recorte-zoom');
      const valor=document.getElementById('recorte-valor');
      const cancelar=document.getElementById('recorte-cancelar');
      const aplicar=document.getElementById('recorte-aplicar');
      const redefinir=document.getElementById('recorte-redefinir');
      const horizontal=document.getElementById('recorte-horizontal');
      const vertical=document.getElementById('recorte-vertical');
      let zoom=1,cx=bitmap.width/2,cy=bitmap.height/2,arrasto=null;
      if(ultimoAjuste?.origem===origem){({zoom,cx,cy}=ultimoAjuste);}
      function desenhar() {
        const r=calcularRecorte(bitmap.width,bitmap.height,zoom,cx,cy);
        cx=r.centroX;cy=r.centroY;
        ctx.clearRect(0,0,canvas.width,canvas.height);
        ctx.drawImage(bitmap,r.x,r.y,r.lado,r.lado,0,0,canvas.width,canvas.height);
        slider.value=String(zoom);valor.value=zoom.toFixed(2)+'×';
        for(const [controle,posicao,limite] of [[horizontal,r.x,bitmap.width-r.lado],[vertical,r.y,bitmap.height-r.lado]]) {
          controle.disabled=limite<1;controle.value=String(limite>0?Math.round(posicao/limite*100):50);
        }
      }
      const limparArrasto=()=>{if(arrasto&&canvas.hasPointerCapture(arrasto.id))canvas.releasePointerCapture(arrasto.id);arrasto=null;canvas.classList.remove('arrastando');};
      return await new Promise((resolve,reject)=>{
        let resultado=null;
        const listeners=[];
        const ouvir=(alvo,tipo,fn)=>{alvo.addEventListener(tipo,fn);listeners.push(()=>alvo.removeEventListener(tipo,fn));};
        const limpar=()=>{listeners.forEach(fn=>fn());limparArrasto();};
        ouvir(modal,'close',()=>{limpar();resolve(resultado);});
        ouvir(cancelar,'click',()=>modal.close());
        ouvir(aplicar,'click',()=>{
          try {
            const r=calcularRecorte(bitmap.width,bitmap.height,zoom,cx,cy);
            const final=document.createElement('canvas');final.width=256;final.height=256;
            final.getContext('2d').drawImage(bitmap,r.x,r.y,r.lado,r.lado,0,0,256,256);
            resultado=final.toDataURL('image/png');modal.close();
            ultimoAjuste={origem,zoom,cx,cy};
          }catch(erro){limpar();modal.close();reject(erro);}
        });
        ouvir(slider,'input',()=>{zoom=Number(slider.value);desenhar();});
        ouvir(horizontal,'input',()=>{const r=calcularRecorte(bitmap.width,bitmap.height,zoom,cx,cy);cx=r.lado/2+(bitmap.width-r.lado)*Number(horizontal.value)/100;desenhar();});
        ouvir(vertical,'input',()=>{const r=calcularRecorte(bitmap.width,bitmap.height,zoom,cx,cy);cy=r.lado/2+(bitmap.height-r.lado)*Number(vertical.value)/100;desenhar();});
        ouvir(redefinir,'click',()=>{zoom=1;cx=bitmap.width/2;cy=bitmap.height/2;desenhar();});
        ouvir(canvas,'pointerdown',e=>{
          if(arrasto||!e.isPrimary||e.button!==0)return;
          e.preventDefault();canvas.focus();canvas.setPointerCapture(e.pointerId);
          arrasto={id:e.pointerId,x:e.clientX,y:e.clientY};canvas.classList.add('arrastando');
        });
        ouvir(canvas,'pointermove',e=>{
          if(!arrasto||e.pointerId!==arrasto.id)return;
          const r=calcularRecorte(bitmap.width,bitmap.height,zoom,cx,cy);
          const caixa=canvas.getBoundingClientRect();
          cx-=(e.clientX-arrasto.x)*r.lado/caixa.width;
          cy-=(e.clientY-arrasto.y)*r.lado/caixa.height;
          arrasto.x=e.clientX;arrasto.y=e.clientY;desenhar();
        });
        ouvir(canvas,'pointerup',limparArrasto);ouvir(canvas,'pointercancel',limparArrasto);
        ouvir(canvas,'lostpointercapture',()=>{arrasto=null;canvas.classList.remove('arrastando');});
        ouvir(canvas,'keydown',e=>{
          const direcoes={ArrowLeft:[1,0],ArrowRight:[-1,0],ArrowUp:[0,1],ArrowDown:[0,-1]};
          if(!direcoes[e.key])return;e.preventDefault();
          const passo=calcularRecorte(bitmap.width,bitmap.height,zoom,cx,cy).lado*(e.shiftKey?.08:.02);
          cx+=direcoes[e.key][0]*passo;cy+=direcoes[e.key][1]*passo;desenhar();
        });
        try {desenhar();modal.showModal();canvas.focus();}catch(erro){limpar();reject(erro);}
      });
    }finally {if(bitmap)bitmap.close();ocupado=false;}
  }
  window.SpectraFoto={abrir,calcularRecorte};
})();
