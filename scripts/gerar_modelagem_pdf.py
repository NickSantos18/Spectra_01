"""Documenta o esquema do código em PDF vetorial, sem acessar dados de usuários."""
import ast
import sqlite3
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'modelagem'
OUT.mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(':memory:')
for name in ('auth/bd.py', 'web/analises.py', 'web/comunidade.py'):
    tree = ast.parse((ROOT/'src/spectra_link_guard'/name).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and 'CREATE TABLE IF NOT EXISTS' in node.value:
            con.executescript(node.value)
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
assert len(tables) == 10
columns = {t:list(con.execute(f'PRAGMA table_info({t})')) for t in tables}
fks = {t:list(con.execute(f'PRAGMA foreign_key_list({t})')) for t in tables}

W,H=1190,842
TEAL='#087e8b'; INK='#162d40'; MUTED='#516779'; LINE='#b4cbd4'; LIGHT='#edf5f7'
pages=[]

def rgb(c): return tuple(int(c[i:i+2],16)/255 for i in (1,3,5))
def color(c): return ' '.join(f'{v:.4f}' for v in rgb(c))
def escape(s):
    raw=s.encode('cp1252',errors='replace')
    return ''.join(chr(b) if 32<=b<127 and chr(b) not in '()\\' else f'\\{b:03o}' for b in raw)

class Page:
    def __init__(self, title, sub, num):
        self.ops=[]
        self.im=Image.new('RGB',(W*2,H*2),'white');self.draw=ImageDraw.Draw(self.im)
        self.text(38,30,'SPECTRA / DOCUMENTAÇÃO DO BANCO',11,TEAL,True)
        self.text(38,56,title,25,INK,True);self.text(38,87,sub,10,MUTED)
        self.line([(38,109),(1152,109)],LINE)
        self.text(38,813,'Esquema SQLite definido no código-fonte • 23/10/2026 • Sem dados pessoais',9,MUTED)
        self.text(1085,813,f'{num} / 3',9,MUTED)
    def text(self,x,y,s,size=10,c=INK,bold=False):
        font='F2' if bold else 'F1'
        self.ops.append(f'BT /{font} {size} Tf {color(c)} rg 1 0 0 1 {x} {H-y-size} Tm ({escape(s)}) Tj ET')
        ft=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',round(size*2))
        self.draw.text((x*2,y*2),s,font=ft,fill=c)
    def box(self,x,y,w,h,fill='white',stroke=LINE):
        fc='#ffffff' if fill=='white' else fill
        self.ops.append(f'{color(fc)} rg {color(stroke)} RG .8 w {x} {H-y-h} {w} {h} re B')
        self.draw.rectangle((x*2,y*2,(x+w)*2,(y+h)*2),fill=fc,outline=stroke,width=2)
    def line(self,pts,c=TEAL,dash=False):
        self.ops.append(f'{color(c)} RG 1 w '+('[4 3] 0 d ' if dash else '[] 0 d ')+f'{pts[0][0]} {H-pts[0][1]} m '+' '.join(f'{x} {H-y} l' for x,y in pts[1:])+' S')
        self.draw.line([(x*2,y*2) for x,y in pts],fill=c,width=2)
    def para(self,x,y,s,width=90,size=10,c=MUTED):
        for row in textwrap.wrap(s,width=width):self.text(x,y,row,size,c);y+=size+5
        return y

def labels(t):
    fk={r[3] for r in fks[t]}
    return [('PK ' if r[5] else '')+('FK ' if r[1] in fk else '')+r[1]+' : '+r[2] for r in columns[t]]

p=Page('Diagrama de entidades e relacionamentos','Modelo físico atual • 10 tabelas • PK = chave primária • FK = chave estrangeira',1)
layout={
 'usuarios':(453,132,280), 'sessoes':(38,132,260), 'perfis':(38,260,260), 'analises':(38,365,260),
 'mensagens':(892,132,260), 'publicacoes':(892,295,260), 'respostas':(892,477,260),
 'seguidores':(453,415,280), 'especialistas':(38,670,260), 'convites_blog':(453,647,280)}
heights={t:31+len(columns[t])*15 for t in tables}
# Linhas desenhadas primeiro para que não cruzem o texto dos cartões.
edges=[
 ([(453,165),(370,165),(370,180),(298,180)],'0..N',304,163),
 ([(453,185),(390,185),(390,300),(298,300)],'0..1',304,283),
 ([(453,205),(410,205),(410,425),(298,425)],'0..N',304,408),
 ([(733,160),(800,160),(800,175),(892,175)],'0..N / remetente',760,138),
 ([(733,190),(780,190),(780,205),(892,205)],'0..N / destinatário',752,209),
 ([(733,235),(818,235),(818,340),(892,340)],'0..N / autor',820,319),
 ([(733,255),(795,255),(795,510),(892,510)],'0..N / autor',800,487),
 ([(520,heights['usuarios']+132),(520,415)],'0..N / seguidor',420,365),
 ([(665,heights['usuarios']+132),(665,415)],'0..N / seguido',675,365),
 ([(1128,295+heights['publicacoes']),(1128,477)],'1 : 0..N',1066,453),
]
for pts,label,x,y in edges:p.line(pts);p.text(x,y,label,8,MUTED)
for t,(x,y,w) in layout.items():
    p.box(x,y,w,heights[t]);p.box(x,y,w,26,TEAL,TEAL);p.text(x+12,y+5,t,12,'#ffffff',True)
    for i,row in enumerate(labels(t)):p.text(x+12,y+32+i*15,row,9)
p.text(453,560,'Leitura das relações',11,TEAL,True)
p.para(453,581,'Cada registro filho aponta para 1 usuário. Um usuário pode possuir zero ou vários registros filhos; o perfil é opcional e único.',46,9)
p.text(38,613,'VÍNCULOS POR E-MAIL: tratados pela aplicação, sem FK no SQLite',11,TEAL,True)
p.para(760,653,'especialistas.email e convites_blog.email são comparados ao e-mail da conta no código. Não há integridade referencial declarada para esses vínculos.',58,10)
p.para(760,724,'seguidores representa a relação N:N entre usuários. mensagens possui duas FKs para usuarios: remetente e destinatário.',58,10)
pages.append(p)

descriptions={
 'usuarios':'Contas locais ou vinculadas ao Google. email e google_sub têm restrição UNIQUE.',
 'sessoes':'Sessões persistentes de autenticação; validade registrada em expira_em.',
 'analises':'Histórico de risco de links por usuário; codigos contém uma lista serializada em JSON.',
 'perfis':'Dados opcionais de apresentação. foto armazena um data URL PNG, não um arquivo separado.',
 'seguidores':'Relação direcionada entre contas. PK composta (seguidor, seguido); CHECK impede seguir a si mesmo.',
 'mensagens':'Mensagens privadas; id inteiro com AUTOINCREMENT. Remetente e destinatário apontam para contas.',
 'publicacoes':'Artigos do blog e tópicos do fórum. tipo é validado pela aplicação como blog ou forum.',
 'respostas':'Comentários das publicações. id inteiro com AUTOINCREMENT; não há árvore de respostas.',
 'especialistas':'Lista de e-mails habilitados a publicar no blog. Não possui FK para usuarios.',
 'convites_blog':'Convites para especialistas. hash guarda SHA-256 do token; usado e expira_em controlam o aceite.'}

def detail(p,t,x,y,w=540):
    p.box(x,y,w,26,TEAL,TEAL);p.text(x+10,y+5,t,12,'#ffffff',True);y+=35
    y=p.para(x+6,y,descriptions[t],87,9)+6
    p.box(x,y,w,20,LIGHT);p.text(x+8,y+4,'Campo',9,INK,True);p.text(x+205,y+4,'Tipo',9,INK,True);p.text(x+280,y+4,'Restrições declaradas / padrão',9,INK,True);y+=24
    fk={r[3] for r in fks[t]}
    for r in columns[t]:
        flags=[]
        if r[5]: flags.append('PK'+(f' #{r[5]}' if t=='seguidores' else ''))
        if r[1] in fk:flags.append('FK')
        if r[3]:flags.append('NOT NULL')
        if r[4] is not None:flags.append('DEFAULT '+r[4])
        if t=='usuarios' and r[1] in ('email','google_sub'):flags.append('UNIQUE')
        p.text(x+8,y,r[1],9);p.text(x+205,y,r[2],9);p.text(x+280,y,', '.join(flags) or '—',9,MUTED);y+=17
    for r in fks[t]:
        p.text(x+8,y,f'FK: {r[3]} -> {r[2]}.{r[4]} | DELETE {r[6]}',8,TEAL);y+=14
    for idx in con.execute(f'PRAGMA index_list({t})'):
        if idx[1].startswith('sqlite_autoindex'):continue
        fields=', '.join(r[2] for r in con.execute(f'PRAGMA index_info({idx[1]})'))
        p.text(x+8,y,f'Índice: {idx[1]} ({fields})',8,MUTED);y+=14
    return y+23

p=Page('Dicionário de dados / identidade e vínculos','Tipos e restrições extraídos dos CREATE TABLE do projeto. Campos sem NOT NULL seguem a declaração SQLite.',2)
y=130
for t in ('usuarios','sessoes','perfis'):y=detail(p,t,38,y)
y=130
for t in ('analises','seguidores'):y=detail(p,t,612,y)
p.text(618,y+6,'Regras da aplicação',12,TEAL,True)
p.para(618,y+31,'E-mails são normalizados em minúsculas. Senhas usam hash scrypt; contas Google podem não ter senha local. Datas são armazenadas em TEXT, geralmente em formato ISO 8601. As sessões têm validade renovável. O histórico mantém até 500 análises por usuário.',86,10)
pages.append(p)

p=Page('Dicionário de dados / comunicação e conteúdo','Integridade referencial habilitada nas conexões por PRAGMA foreign_keys = ON.',3)
y=130
for t in ('mensagens','publicacoes','respostas'):y=detail(p,t,38,y)
y=130
for t in ('especialistas','convites_blog'):y=detail(p,t,612,y)
p.text(618,y+3,'Observações do modelo atual',12,TEAL,True)
y=p.para(618,y+29,'O IP mostrado no perfil vem da conexão HTTP e não é uma coluna do banco. Explorar é uma consulta de publicações, não uma tabela. O chat não tem tabela de conversas: os participantes são inferidos de remetente e destinatário.',86,10)+12
y=p.para(618,y,'Os e-mails dos editores são definidos por SPECTRA_EDITOR_EMAILS, fora do banco. A autorização para conversar depende de existir uma relação de seguidores em algum sentido.',86,10)+12
y=p.para(618,y,'Exclusões: FKs com CASCADE removem filhos automaticamente. O autor de publicacoes e respostas usa NO ACTION: esses vínculos podem impedir a exclusão da conta enquanto houver conteúdo associado.',86,10)+12
p.para(618,y,'Fontes: src/spectra_link_guard/auth/bd.py; web/analises.py; web/comunidade.py. Documento gerado a partir do esquema no código, sem leitura dos registros do banco local.',86,9)
pages.append(p)

# PDF vetorial: texto selecionável, fontes padrão e desenhos em coordenadas PDF.
objects=[b'',b'',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>']
kids=[]
for page in pages:
    content='\n'.join(page.ops).encode('ascii')
    stream_id=len(objects)+1
    objects.append(f'<< /Length {len(content)} >>\nstream\n'.encode()+content+b'\nendstream')
    page_id=len(objects)+1;kids.append(page_id)
    objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {stream_id} 0 R >>'.encode())
objects[0]=b'<< /Type /Catalog /Pages 2 0 R >>'
objects[1]=f'<< /Type /Pages /Kids [{" ".join(str(i)+" 0 R" for i in kids)}] /Count {len(kids)} >>'.encode()
pdf=bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n');offsets=[0]
for i,obj in enumerate(objects,1):
    offsets.append(len(pdf));pdf.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
xref=len(pdf);pdf.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
for off in offsets[1:]:pdf.extend(f'{off:010d} 00000 n \n'.encode())
pdf.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
path=OUT/'Spectra-modelagem-banco-de-dados.pdf';path.write_bytes(pdf)
for i,page in enumerate(pages,1):page.im.save(OUT/f'pagina-{i}.png')
print(f'PDF criado: {path} ({len(pdf):,} bytes), {len(pages)} páginas; {len(tables)} tabelas, {sum(map(len,fks.values()))} FKs.')
