"""Destinos públicos para o handshake. O socket usa o IP já validado."""
import ipaddress
import socket

class DestinoBloqueado(ValueError): pass

def ip_publico(valor):
    ip=ipaddress.ip_address(valor.split('%')[0])
    if isinstance(ip,ipaddress.IPv6Address):
        if ip.ipv4_mapped: return ip_publico(str(ip.ipv4_mapped))
        if ip.sixtofour or ip.teredo: return False
        if ip in ipaddress.ip_network('64:ff9b::/96') or ip in ipaddress.ip_network('64:ff9b:1::/48'): return False
    return ip.is_global and not (ip.is_multicast or ip.is_reserved or ip.is_unspecified)

def resolver_publico(host, porta):
    if porta!=443: raise DestinoBloqueado('A análise TLS permite somente a porta 443.')
    infos=socket.getaddrinfo(host,porta,type=socket.SOCK_STREAM,proto=socket.IPPROTO_TCP)
    if not infos or any(not ip_publico(i[4][0]) for i in infos):
        raise DestinoBloqueado('Destinos internos ou especiais não podem ser consultados.')
    return list(dict.fromkeys((i[0],i[1],i[2],i[4]) for i in infos))

def conectar(destinos, timeout):
    erro=None
    for familia,tipo,protocolo,endereco in destinos:
        if not ip_publico(endereco[0]) or endereco[1]!=443: raise DestinoBloqueado('Destino bloqueado.')
        s=socket.socket(familia,tipo,protocolo)
        try:
            s.settimeout(timeout); s.connect(endereco); return s
        except OSError as e:
            erro=e; s.close()
    raise erro or OSError('Nenhum destino acessível.')
