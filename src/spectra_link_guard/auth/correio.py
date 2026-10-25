"""Envio SMTP explícito. Sem provedor, não afirma que enviou mensagens."""
from email.message import EmailMessage
import logging
import os
import smtplib
import ssl
from . import bd,fluxos,protecao

log=logging.getLogger('spectra.correio')
def configurado(): return bool(os.getenv('SPECTRA_SMTP_HOST') and os.getenv('SPECTRA_SMTP_REMETENTE'))

def enviar(destinatario,assunto,texto):
    msg=EmailMessage()
    msg['From']=os.environ['SPECTRA_SMTP_REMETENTE'];msg['To']=destinatario;msg['Subject']=assunto
    msg.set_content(texto)
    porta=int(os.getenv('SPECTRA_SMTP_PORTA','587'))
    classe=smtplib.SMTP_SSL if porta==465 else smtplib.SMTP
    kwargs={'context':ssl.create_default_context()} if porta==465 else {}
    with classe(os.environ['SPECTRA_SMTP_HOST'],porta,timeout=10,**kwargs) as smtp:
        if porta!=465: smtp.starttls(context=ssl.create_default_context())
        if os.getenv('SPECTRA_SMTP_USUARIO'): smtp.login(os.environ['SPECTRA_SMTP_USUARIO'],os.environ['SPECTRA_SMTP_SENHA'])
        smtp.send_message(msg)

def solicitar(email,finalidade):
    try:
        u=bd.buscar_por_email(email)
        if not u or (finalidade=='verificar' and u['email_verificado']): return
        token=fluxos.emitir(u,finalidade)
        pagina='confirmar-email' if finalidade=='verificar' else 'redefinir-senha'
        link=protecao.origem_publica()+'/'+pagina+'#token='+token
        enviar(u['email'],'Spectra: confirme seu e-mail' if finalidade=='verificar' else 'Spectra: redefina sua senha',
               'Abra este link em até 20 minutos:\n\n'+link+'\n\nSe você não solicitou, ignore esta mensagem.')
    except Exception:
        # Endereços, tokens e credenciais não entram no log.
        log.error('Não foi possível concluir o envio de e-mail de acesso.')
