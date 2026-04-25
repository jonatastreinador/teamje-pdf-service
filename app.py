"""
TEAMJE PDF Service - Dinamico v2
Suporta qualquer numero de refeicoes (3, 4, 5, 6...)
Deploy: Render.com
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import io, base64, os, tempfile

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

from logo_data import LOGO_B64, WM_B64

app  = Flask(__name__)
CORS(app)

W, H    = A4
PRETO   = colors.HexColor('#0D0D0D')
CINZA_L = colors.HexColor('#F4F4F4')
CINZA_B = colors.HexColor('#E0E0E0')
CINZA_T = colors.HexColor('#444444')
BRANCO  = colors.white

def get_logos():
    tmp  = tempfile.gettempdir()
    logo = os.path.join(tmp, 'teamje_logo.png')
    wm   = os.path.join(tmp, 'teamje_wm.png')
    if not os.path.exists(logo):
        with open(logo, 'wb') as f: f.write(base64.b64decode(LOGO_B64))
    if not os.path.exists(wm):
        with open(wm,   'wb') as f: f.write(base64.b64decode(WM_B64))
    return logo, wm

class BG:
    def __init__(self, logo, wm): self.logo, self.wm = logo, wm
    def __call__(self, canv, doc):
        canv.saveState()
        canv.setFillColor(BRANCO)
        canv.rect(0, 0, W, H, fill=1, stroke=0)
        canv.drawImage(self.wm,   0, 0, W, H, preserveAspectRatio=False, mask='auto')
        canv.drawImage(self.logo, W-4.6*cm, H-1.6*cm, 4.1*cm, 1.3*cm, preserveAspectRatio=True, mask='auto')
        canv.drawImage(self.logo, W/2-2.3*cm, 0.2*cm,  4.6*cm, 1.5*cm, preserveAspectRatio=True, mask='auto')
        canv.restoreState()

def S(name, **kw):
    base = dict(fontName='Helvetica', fontSize=9.5, textColor=PRETO, leading=13, spaceAfter=3)
    base.update(kw)
    return ParagraphStyle(name, **base)

def banner(t1, t2=''):
    rows = [[Paragraph(f'<b>{t1}</b>', S('b1', fontName='Helvetica-Bold', fontSize=13, textColor=BRANCO, alignment=TA_CENTER, leading=18))]]
    if t2: rows.append([Paragraph(f'<b>{t2}</b>', S('b2', fontName='Helvetica-Bold', fontSize=10, textColor=BRANCO, alignment=TA_CENTER, leading=14))])
    t = Table(rows, colWidths=[W-3.6*cm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PRETO),('ALIGN',(0,0),(-1,-1),'CENTER'),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
    return t

def pill(label):
    p = Paragraph(f'<b>{label.upper()}</b>', S('pl', fontName='Helvetica-Bold', fontSize=11, textColor=BRANCO, alignment=TA_CENTER, leading=16))
    inn = Table([[p]], colWidths=[8.5*cm])
    inn.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PRETO),('ALIGN',(0,0),(-1,-1),'CENTER'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LEFTPADDING',(0,0),(-1,-1),20),('RIGHTPADDING',(0,0),(-1,-1),20),('ROUNDEDCORNERS',[20])]))
    out = Table([[inn]], colWidths=[W-3.6*cm])
    out.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER')]))
    return out

def meal_table(itens, avontade=''):
    hdr = [Paragraph('<b>Categoria</b>',S('th',fontName='Helvetica-Bold',fontSize=9,textColor=BRANCO,alignment=TA_CENTER)),
           Paragraph('<b>Opcoes</b>',   S('th2',fontName='Helvetica-Bold',fontSize=9,textColor=BRANCO,alignment=TA_CENTER))]
    data = [hdr]
    for item in itens:
        cat  = item.get('categoria','')
        opts = item.get('opcoes','')
        data.append([Paragraph(f'<b>{cat}</b>',S('cat',fontName='Helvetica-Bold',fontSize=9,textColor=PRETO,alignment=TA_CENTER,leading=12)),
                     Paragraph(opts,           S('opt',fontSize=9,textColor=PRETO,alignment=TA_CENTER,leading=12))])
    if avontade:
        data.append([Paragraph('<b>A-vontade</b>',S('avc',fontName='Helvetica-Bold',fontSize=9,textColor=PRETO,alignment=TA_CENTER,leading=12)),
                     Paragraph(avontade,          S('avo',fontSize=9,textColor=PRETO,alignment=TA_CENTER,leading=12))])
    t = Table(data, colWidths=[3.2*cm,13.3*cm], repeatRows=1)
    even = [('BACKGROUND',(0,i),(-1,i),CINZA_L) for i in range(2,len(data),2)]
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PRETO),('TEXTCOLOR',(0,0),(-1,0),BRANCO),('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),('GRID',(0,0),(-1,-1),0.4,CINZA_B),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7)]+even))
    return t

def gerar_pdf_dieta(dados):
    logo, wm = get_logos()
    bg = BG(logo, wm)

    nome  = dados.get('nome','ALUNO').upper()
    num   = str(dados.get('numero','1'))
    data  = dados.get('data','---')
    kcal  = str(dados.get('kcal','2000'))

    # Refeicoes dinamicas
    refeicoes = dados.get('refeicoes', [])
    if not refeicoes:
        for key, nref in [('cafe_manha','CAFE DA MANHA'),('almoco','ALMOCO'),('lanche_tarde','LANCHE DA TARDE'),('jantar','JANTAR')]:
            itens = dados.get(key, [])
            if itens: refeicoes.append({'nome':nref,'itens':itens,'avontade':dados.get(key+'_avontade','')})

    suplementos    = dados.get('suplementos',    [])
    rec_cardio     = dados.get('rec_cardio',     'Incorpore cardio 5 a 7 vezes por semana, 30 min/dia.')
    rec_agua       = dados.get('rec_agua',       '35 ml por kg de peso por dia.')
    rec_musculacao = dados.get('rec_musculacao', 'Treine 4 a 5 vezes por semana com foco em musculacao.')
    rec_dicas      = dados.get('rec_dicas',      [])

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=1.8*cm, bottomMargin=2.6*cm)
    st  = []

    # Header
    tit = Paragraph(f'<b>PROTOCOLO DIETETICO {num}: {nome}</b>', S('ht',fontName='Helvetica-Bold',fontSize=14,textColor=PRETO,leading=18))
    sub = Paragraph(f'DATA {data}&nbsp;&nbsp;&nbsp;&nbsp;{kcal}kcal', S('hs',fontSize=10,textColor=CINZA_T,leading=14))
    hdr = Table([[tit,''],[sub,'']], colWidths=[13.0*cm,2.8*cm])
    hdr.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LINEBELOW',(0,1),(-1,1),2,PRETO),('BOTTOMPADDING',(0,1),(-1,1),6)]))
    st.append(hdr); st.append(Spacer(1,8))
    st.append(banner('REFEICOES')); st.append(Spacer(1,8))

    for txt in ['PASSO-A-PASSO PARA MONTAR REFEICOES:','ESCOLHA UMA OPCAO DE CADA CATEGORIA PARA CADA REFEICAO.']:
        st.append(Paragraph(f'<b>{txt}</b>', S('pp',fontName='Helvetica-Bold',fontSize=9.5,textColor=PRETO,alignment=TA_CENTER,leading=14)))
    st.append(Spacer(1,4))
    for lbl in ['Carboidrato','Proteina','Gordura','Fruta']:
        rest = ': Escolha uma opcao ou mais respeitando as 150g' if lbl=='Fruta' else ': Escolha uma opcao'
        st.append(Paragraph(f'<b><font color="#1565C0">{lbl}:</font></b>{rest}', S('pc',fontSize=9.5,alignment=TA_CENTER,leading=13)))
    st.append(Spacer(1,10))

    # Refeicoes dinamicas - 2 por pagina
    for idx, ref in enumerate(refeicoes):
        nome_ref = ref.get('nome', f'REFEICAO {idx+1}')
        itens    = ref.get('itens', [])
        avontade = ref.get('avontade', '')
        if not itens: continue
        st.append(pill(nome_ref)); st.append(Spacer(1,6))
        st.append(meal_table(itens, avontade))
        is_last = (idx == len(refeicoes)-1)
        if (idx+1) % 2 == 0 or is_last:
            st.append(PageBreak())
        else:
            st.append(Spacer(1,14))

    # Recomendacoes
    st.append(banner('RECOMENDACOES')); st.append(Spacer(1,10))
    for b,tx in [('CARDIO: SEMPRE BEM-VINDO!',rec_cardio),('AGUA E VIDA: ADOTE UMA GARRAFA!',rec_agua),('MUSCULACAO: FOCO NO TREINO!',rec_musculacao)]:
        st.append(Paragraph(f'<b>{b}</b> {tx}', S('ri',fontSize=9.5,textColor=PRETO,leading=14,spaceAfter=7,alignment=TA_JUSTIFY)))
    if rec_dicas:
        st.append(Paragraph('<b>DICAS ESSENCIAIS:</b>', S('dk',fontName='Helvetica-Bold',fontSize=9.5,textColor=PRETO,spaceAfter=3)))
        for d in rec_dicas:
            st.append(Paragraph(f'+ {d}', S('di',fontSize=9.5,textColor=PRETO,leading=13,leftIndent=10,spaceAfter=3)))
    st.append(Spacer(1,14))

    # Refeicao Livre intro
    st.append(banner('REFEICAO LIVRE','CORRETAMENTE')); st.append(Spacer(1,10))
    for tx in ['Se voce acha que dieta e sinonimo de sofrimento ou que precisa viver a base de frango e batata-doce para ter resultado... respira.','A refeicao livre existe justamente para quebrar essa ideia. Ela e uma ferramenta estrategica - e nao uma desculpa para exagerar. Quando usada com consciencia, pode melhorar sua adesao, controlar a ansiedade e ate acelerar seus resultados por ajudar no equilibrio psicologico.']:
        st.append(Paragraph(tx, S('rl',fontSize=9.5,textColor=PRETO,leading=14,spaceAfter=7,alignment=TA_JUSTIFY)))
    st.append(PageBreak())

    # Refeicao Livre detalhada
    st.append(banner('REFEICAO LIVRE','CORRETAMENTE')); st.append(Spacer(1,10))
    for bold,items in [
        ('O QUE E UMA REFEICAO LIVRE?',['E uma ou duas refeicoes na semana em que voce pode comer algo fora do seu plano alimentar, sem se preocupar com pesar alimentos, contar macros ou seguir uma estrutura rigida. Mas atencao: livre nao e sinonimo de descontrolado.']),
        ('QUANDO FAZER?',['- 1 vez por semana','- Substituindo ate 2 refeicoes da sua dieta no mesmo dia']),
        ('Exemplo:',['- Almoco com sua familia (churrasco, feijoada, etc.)','- Jantar com amigos (hamburguer, pizza, etc.)']),
        ('OBJETIVOS DA REFEICAO LIVRE:',['- Reduzir ansiedade e compulsao','- Melhorar a adesao ao plano alimentar','- Aumentar momentaneamente a leptina','- Recuperar energia fisica e mental','- Tornar o processo mais leve e sustentavel']),
        ('CUIDADOS IMPORTANTES',['- Evite transformar a refeicao livre em um dia inteiro de exageros.','- Nao compense no dia seguinte com jejum ou restricoes extremas.','- Evite alimentos que te causam desconforto ou alergias.','- Cuidado com o alcool em excesso.']),
    ]:
        st.append(Paragraph(f'<b>{bold}</b>', S('h4',fontName='Helvetica-Bold',fontSize=9.5,textColor=PRETO,spaceAfter=2)))
        for it in items: st.append(Paragraph(it, S('l4',fontSize=9.5,textColor=PRETO,leading=13,leftIndent=8,spaceAfter=2,alignment=TA_JUSTIFY)))
        st.append(Spacer(1,4))
    st.append(PageBreak())

    # Refeicao Livre cont
    st.append(banner('REFEICAO LIVRE','CORRETAMENTE')); st.append(Spacer(1,10))
    for bold,items in [
        ('DICAS PARA FAZER DA FORMA CERTA',['- Planeje com antecedencia o dia e a refeicao','- Aproveite o momento com prazer, mas com consciencia','- Coma devagar, mastigue bem e observe os sinais de saciedade','- Se possivel, inclua alimentos que voce gosta MUITO']),
        ('RESUMO PRATICO',['- Frequencia: 1x na semana','- Quantidade: ate 2 refeicoes do dia','- Regra de ouro: Aproveite, mas nao exagere!']),
    ]:
        st.append(Paragraph(f'<b>{bold}</b>', S('h5',fontName='Helvetica-Bold',fontSize=9.5,textColor=PRETO,spaceAfter=2)))
        for it in items: st.append(Paragraph(it, S('l5',fontSize=9.5,textColor=PRETO,leading=13,leftIndent=8,spaceAfter=2)))
        st.append(Spacer(1,6))
    st.append(Paragraph('Lembre-se: o equilibrio e o que faz uma dieta funcionar no longo prazo. Voce nao precisa ser perfeito, so precisa ser consistente.', S('lm',fontSize=9.5,textColor=PRETO,leading=14,spaceAfter=8,alignment=TA_JUSTIFY)))
    st.append(Paragraph('<b>CONSIDERACOES FINAIS</b>', S('cf',fontName='Helvetica-Bold',fontSize=9.5,textColor=PRETO,spaceAfter=2)))
    st.append(Paragraph('A refeicao livre existe para voce seguir firme na sua jornada - nao como fuga, mas como estrategia. Se usada com maturidade, ela ajuda a manter o plano de forma leve, prazerosa e sem culpa.', S('cfb',fontSize=9.5,textColor=PRETO,leading=14,spaceAfter=6,alignment=TA_JUSTIFY)))
    st.append(Paragraph('Agora que voce sabe como funciona, use com sabedoria e continue evoluindo no seu processo!', S('cfb2',fontSize=9.5,textColor=PRETO,leading=14,alignment=TA_JUSTIFY)))
    st.append(PageBreak())

    # Suplementos
    st.append(banner('SUPLEMENTOS','BASICOS')); st.append(Spacer(1,14))
    if suplementos:
        for sup in suplementos:
            nd = str(sup.get('nome','')).strip()
            hr = str(sup.get('horario','')).strip()
            jf = str(sup.get('justificativa','')).strip()
            if not nd: continue
            linha = f'<b>{nd}</b>' + (f' -> {hr}' if hr else '')
            st.append(Paragraph(linha, S('sn',fontName='Helvetica-Bold',fontSize=9.5,textColor=PRETO,leading=13,spaceAfter=1)))
            if jf: st.append(Paragraph(f'Por que? {jf}', S('sj',fontSize=9,textColor=CINZA_T,leading=13,spaceAfter=9,alignment=TA_JUSTIFY)))
            else:   st.append(Spacer(1,8))
    else:
        for nd,hr,jf in [
            ('OMEGA 3 1000MG 1DOSE/DIA','junto a primeira refeicao','Essencial para saude cardiovascular, reduz inflamacoes e auxilia na recuperacao muscular.'),
            ('VITAMINA D 2.000UI 1 DOSE/DIA','junto a primeira refeicao','Essencial para saude ossea, imunidade e equilibrio hormonal.'),
            ('MULTIVITIAMINICO 1 DOSE/DIA','junto a primeira refeicao','Repoe vitaminas e minerais, mantem o metabolismo funcionando.'),
            ('COMPLEXO B 1 DOSE/DIA','junto a primeira refeicao','Fundamental para metabolismo energetico, disposicao e sintese proteica.'),
        ]:
            st.append(Paragraph(f'<b>{nd}</b> -> {hr}', S('sn2',fontName='Helvetica-Bold',fontSize=9.5,textColor=PRETO,leading=13,spaceAfter=1)))
            st.append(Paragraph(f'Por que? {jf}', S('sj2',fontSize=9,textColor=CINZA_T,leading=13,spaceAfter=9,alignment=TA_JUSTIFY)))
    st.append(PageBreak())

    # Higiene do Sono
    st.append(banner('HIGIENE DO SONO')); st.append(Spacer(1,10))
    st.append(Paragraph('Uma noite mal dormida nao apenas prejudicara o crescimento muscular ou o emagrecimento, mas tambem estimulara o catabolismo. Para assegurar a recuperacao muscular, e fundamental desfrutar de uma noite de sono adequada.', S('so',fontSize=9.5,textColor=PRETO,leading=14,spaceAfter=10,alignment=TA_JUSTIFY)))
    for tit,desc,dica in [
        ('USE CHAS RELAXANTES ANTES DE DORMIR','Ervas como passiflora, mulungu e melissa tem propriedades calmantes que favorecem o relaxamento.','Evite chas com cafeina. Tome o cha cerca de 30 minutos antes de dormir.'),
        ('AROMATIZE O AMBIENTE COM OLEOS ESSENCIAIS','Aromas suaves como lavanda e laranja doce podem reduzir a tensao e criar clima propicio ao sono.','Utilize difusores ou velas aromaticas seguras para uso noturno.'),
        ('EVITE ESTIMULANTES APOS AS 18H','Substancias como cafeina e nicotina interferem no ciclo do sono.','Fique atento a medicamentos e suplementos que contenham cafeina.'),
        ('CRIE UM RITUAL DE RELAXAMENTO ANTES DE DORMIR','Respiracao profunda, leitura leve ou meditacao ajudam a desacelerar corpo e mente.','Crie uma rotina simples e repita todos os dias.'),
        ('REDUZA A EXPOSICAO A LUZES FORTES A NOITE','Ambientes muito iluminados dificultam a producao de melatonina.',''),
    ]:
        st.append(Paragraph(f'<b>{tit}</b> Por que: {desc}', S('si',fontSize=9.5,textColor=PRETO,leading=14,spaceAfter=2,alignment=TA_JUSTIFY)))
        if dica: st.append(Paragraph(f'<b>Dica:</b> {dica}', S('sd',fontSize=9.5,textColor=PRETO,leading=13,leftIndent=10,spaceAfter=6)))
        else: st.append(Spacer(1,6))
    st.append(Paragraph('<b>DICA EXTRA:</b> Garanta um ambiente favoravel ao sono: quarto escuro, silencioso e fresco. Horarios regulares para dormir e acordar. Evite usar o quarto para trabalhar.', S('de',fontSize=9.5,textColor=PRETO,leading=14,alignment=TA_JUSTIFY)))

    doc.build(st, onFirstPage=bg, onLaterPages=bg)
    buf.seek(0)
    return buf

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status':'ok','service':'TEAMJE PDF Service v2 - Dinamico'})

@app.route('/gerar-dieta', methods=['POST'])
def gerar_dieta():
    try:
        dados = request.get_json(force=True)
        if not dados: return jsonify({'error':'Dados nao enviados'}), 400
        buf   = gerar_pdf_dieta(dados)
        nome  = dados.get('nome','aluno').replace(' ','-').lower()
        num   = dados.get('numero','1')
        fname = f'Dieta-{num}-{nome}.pdf'
        return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=fname)
    except Exception as e:
        import traceback
        return jsonify({'error':str(e),'trace':traceback.format_exc()}), 500

@app.route('/', methods=['GET'])
def index():
    return jsonify({'service':'TEAMJE PDF Service','version':'2.0 Dinamico','info':'Suporta qualquer numero de refeicoes'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


# ════════════════════════════════════════════════════════════════════
# AVALIAÇÃO POSTURAL — gerador integrado
# ════════════════════════════════════════════════════════════════════
from PIL import Image as PILImage, ImageDraw, ImageFont
import io as _io

_POST_LOGO = None
def _plogo():
    global _POST_LOGO
    if _POST_LOGO is None:
        _POST_LOGO = PILImage.open('/tmp/teamje_logo.png').convert('RGBA')
    return _POST_LOGO

def _paste_logo_post(img, h=68, pad=22):
    l = _plogo()
    w2 = int(l.width*h/l.height)
    lr = l.resize((w2,h), PILImage.LANCZOS)
    img.paste(lr,(img.width-w2-pad,img.height-h-pad),lr)

_PFP  = None
_PFPR = None
_PFC  = {}
def _PF(sz, bold=True):
    k=(sz,bold)
    if k not in _PFC:
        global _PFP, _PFPR
        if _PFP is None:
            for p in ['/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf',
                      '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
                try: _PFP=ImageFont.truetype(p,12); break
                except: pass
            for p in ['/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf',
                      '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
                try: _PFPR=ImageFont.truetype(p,12); break
                except: pass
        try:
            path = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf' if bold else '/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf'
            _PFC[k] = ImageFont.truetype(path, sz)
        except:
            _PFC[k] = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', sz)
    return _PFC[k]

def _ptw(d,t,f): b=d.textbbox((0,0),t,font=f); return b[2]-b[0]
def _pth(d,t,f): b=d.textbbox((0,0),t,font=f); return b[3]-b[1]
def _pctext(d,t,cx,y,f,fill=(255,255,255)): d.text((cx-_ptw(d,t,f)//2,y),t,font=f,fill=fill)
def _pwrap(d,text,font,max_w):
    words=text.split(); lines=[]; cur=[]
    for w in words:
        test=' '.join(cur+[w])
        if _ptw(d,test,font)>max_w and cur:
            lines.append(' '.join(cur)); cur=[w]
        else: cur.append(w)
    if cur: lines.append(' '.join(cur))
    return lines

def _fit_box(draw,text,ix,iy,iw,max_bottom,fs=48,fmin=24,bold=True):
    for sz in range(fs,fmin-1,-2):
        f=_PF(sz,bold=bold); lh=int(sz*1.38)
        ls=_pwrap(draw,text,f,iw)
        if iy+len(ls)*lh<=max_bottom: return f,ls,lh
    f=_PF(fmin,bold=bold); lh=int(fmin*1.38)
    return f,_pwrap(draw,text,f,iw),lh

def _post_make_bg():
    NAVY=(6,16,48)
    img=PILImage.new('RGB',(1920,1080),NAVY)
    draw=ImageDraw.Draw(img)
    for i in range(-1080,1920+1080,55):
        draw.line([(i,0),(i+1080,1080)],fill=tuple(max(0,c-9) for c in NAVY),width=2)
    draw.polygon([(1420,0),(1920,0),(1920,340)],fill=(14,30,82))
    draw.polygon([(1740,0),(1920,0),(1920,130)],fill=(18,38,105))
    draw.polygon([(0,820),(300,1080),(0,1080)],fill=(14,30,82))
    draw.polygon([(1600,1080),(1920,880),(1920,1080)],fill=(14,30,82))
    return img

def _post_slide_capa(nome,numero,data):
    img=_post_make_bg(); draw=ImageDraw.Draw(img); cx=960
    BLUE=(26,99,255); WHITE=(255,255,255); OFF_W=(210,222,255)
    y=70; _pctext(draw,f'AVALIACAO {numero}',cx,y,_PF(65))
    y+=108; _pctext(draw,'POSTURAL',cx,y,_PF(142))
    y+=162; _pctext(draw,nome.upper(),cx,y,_PF(116))
    y+=146; bw=300
    draw.rounded_rectangle([cx-bw//2,y,cx+bw//2,y+74],radius=9,fill=BLUE)
    _pctext(draw,'TEAM JE',cx,y+12,_PF(44))
    _pctext(draw,data,cx,y+92,_PF(48,bold=False),fill=OFF_W)
    _paste_logo_post(img,h=92,pad=40)
    return img

def _post_slide_atencao():
    img=_post_make_bg(); draw=ImageDraw.Draw(img); cx=960
    BLUE=(26,99,255); WHITE=(255,255,255)
    f_b=_PF(72); bw=_ptw(draw,'ATENCAO',f_b)+110
    draw.rounded_rectangle([cx-bw//2,85,cx+bw//2,179],radius=10,fill=BLUE)
    _pctext(draw,'ATENCAO',cx,97,f_b)
    f_t=_PF(50); y=235
    for ln in ['Tudo que voce encontrar nesse PDF, provavelmente',
               'nenhum outro profissional te falou ou analisou.','',
               'O seu treino e a escolha de quais alongamentos voce','ira fazer e baseado nesta avaliacao postural;','',
               'Entao siga a risca e nunca compartilhe seu treino','com outras pessoas!']:
        if ln:
            lw=_ptw(draw,ln,f_t); draw.text((cx-lw//2,y),ln,font=f_t,fill=WHITE)
        y+=74
    _paste_logo_post(img,h=80,pad=28)
    return img

def _post_slide_resultados():
    img=_post_make_bg(); draw=ImageDraw.Draw(img); cx=960
    BLUE=(26,99,255); WHITE=(255,255,255)
    f_b=_PF(106); bw=_ptw(draw,'RESULTADOS',f_b)+130
    draw.rounded_rectangle([cx-bw//2,145,cx+bw//2,295],radius=10,fill=BLUE)
    _pctext(draw,'RESULTADOS',cx,158,f_b)
    f_t=_PF(90); y=348
    for txt in ['POSITIVO = ENCURTADO','NEGATIVO = NORMAL']:
        lw=_ptw(draw,txt,f_t); draw.text((cx-lw//2,y),txt,font=f_t,fill=WHITE); y+=152
    _paste_logo_post(img,h=80,pad=28)
    return img

def _post_foto_slot(img,draw,x,y,w,h,b64=None,label=''):
    NAVY2=(12,26,70); OFF_W=(210,222,255); WHITE=(255,255,255)
    if b64:
        try:
            raw=base64.b64decode(b64)
            fi=PILImage.open(_io.BytesIO(raw)).convert('RGB')
            ratio=min(w/fi.width,h/fi.height)
            nw,nh=int(fi.width*ratio),int(fi.height*ratio)
            fi=fi.resize((nw,nh),PILImage.LANCZOS)
            img.paste(fi,(x+(w-nw)//2,y+(h-nh)//2))
            if label:
                f_l=_PF(28); lw=_ptw(draw,label,f_l)
                draw.rectangle([x+(w-lw)//2-6,y+h-44,x+(w+lw)//2+6,y+h-8],fill=(0,0,0))
                draw.text((x+(w-lw)//2,y+h-42),label,font=f_l,fill=WHITE)
            return
        except: pass
    draw.rounded_rectangle([x+4,y+4,x+w-4,y+h-4],radius=12,fill=NAVY2,outline=(55,95,210),width=3)
    iy2=y+h//2-80
    for txt,sz,clr in [('FOTO DO ALUNO',34,(100,150,240)),('com anotacoes da IA',26,(80,120,200)),('(linhas, pontos, angulos)',24,(70,110,185))]:
        f2=_PF(sz,bold=(sz>26)); lw=_ptw(draw,txt,f2)
        draw.text((x+(w-lw)//2,iy2),txt,font=f2,fill=clr); iy2+=int(sz*1.6)
    if label:
        f_l=_PF(30); lw=_ptw(draw,label,f_l)
        draw.text((x+(w-lw)//2,y+h-48),label,font=f_l,fill=OFF_W)

def _post_slide_teste(nome_teste,resultado,fotos_b64,diagnostico,
                      angulos='',musculos='',prioridade='Alta',num_fotos=1):
    BLUE=(26,99,255); WHITE=(255,255,255); OFF_W=(210,222,255)
    RED_A=(255,72,72); GREEN_A=(45,230,95); YELLOW_A=(255,195,35)
    img=_post_make_bg(); draw=ImageDraw.Draw(img)
    BH=114
    draw.rounded_rectangle([36,18,1884,132],radius=12,fill=BLUE)
    f_tt=_PF(78)
    while _ptw(draw,nome_teste.upper(),f_tt)>1800 and f_tt.size>44: f_tt=_PF(f_tt.size-3)
    _pctext(draw,nome_teste.upper(),960,18+(BH-_pth(draw,'A',f_tt))//2,f_tt)
    cy=148; ch=912; PAD=16
    n=max(1,min(int(num_fotos),2))
    fz_x=36; fz_w=910; fz_y=cy; fz_h=ch
    if n==2:
        fw=(fz_w-PAD)//2
        slots=[(fz_x,fz_y,fw,fz_h),(fz_x+fw+PAD,fz_y,fw,fz_h)]; lbls=['FOTO 1','FOTO 2']
    else:
        slots=[(fz_x,fz_y,fz_w,fz_h)]; lbls=['']
    for i,(sx,sy,sw,sh) in enumerate(slots):
        b64=(fotos_b64[i] if fotos_b64 and i<len(fotos_b64) else None)
        _post_foto_slot(img,draw,sx,sy,sw,sh,b64,lbls[i] if n==2 else '')
    BX=966; BW=918; BY=cy; BH2=ch
    IX=BX+26; IW=BW-52; IY=BY+20; IB=BY+BH2-18
    draw.rounded_rectangle([BX,BY,BX+BW,BY+BH2],radius=16,fill=BLUE)
    is_pos='POSITIVO' in resultado.upper() and 'NEGATIVO' not in resultado.upper()
    rcol=RED_A if is_pos else GREEN_A
    f_res=_PF(42); draw.text((IX,IY),resultado.upper(),font=f_res,fill=rcol)
    iy=IY+_pth(draw,'A',f_res)+12
    draw.line([(IX,iy),(IX+IW,iy)],fill=(190,210,255),width=2); iy+=14
    FOOTER_H=155; diag_max=IB-FOOTER_H
    f_diag,ls_diag,lh_diag=_fit_box(draw,diagnostico,IX,iy,IW,diag_max,fs=50,fmin=26,bold=True)
    for line in ls_diag: draw.text((IX,iy),line,font=f_diag,fill=WHITE); iy+=lh_diag
    iy=IB-FOOTER_H+8
    draw.line([(IX,iy),(IX+IW,iy)],fill=(190,210,255),width=1); iy+=10
    if musculos:
        f_ml,ls_ml,lh_ml=_fit_box(draw,'MUSCULOS: '+musculos,IX,iy,IW,IB-72,fs=29,fmin=20,bold=False)
        for line in ls_ml:
            if iy+lh_ml>IB-68: break
            draw.text((IX,iy),line,font=f_ml,fill=OFF_W); iy+=lh_ml
    if angulos and iy<IB-58:
        f_ang,ls_ang,lh_ang=_fit_box(draw,f'ANGULO: {angulos}',IX,iy,IW,IB-44,fs=28,fmin=20,bold=True)
        for line in ls_ang:
            if iy+lh_ang>IB-40: break
            draw.text((IX,iy),line,font=f_ang,fill=WHITE); iy+=lh_ang
    if prioridade:
        f_p=_PF(32); pcol=RED_A if 'Alta' in prioridade else YELLOW_A if 'Media' in prioridade or 'Média' in prioridade else GREEN_A
        ptxt=f'PRIORIDADE: {prioridade.upper()}'
        while _ptw(draw,ptxt,f_p)>IW and f_p.size>20: f_p=_PF(f_p.size-2)
        draw.text((IX,IB-_pth(draw,'A',f_p)-14),ptxt,font=f_p,fill=pcol)
    _paste_logo_post(img,h=60,pad=16)
    return img

def _post_slide_encerramento():
    img=_post_make_bg(); draw=ImageDraw.Draw(img); cx=960; BLUE=(26,99,255)
    _pctext(draw,'AQUI O TREINO E',cx,248,_PF(120))
    _pctext(draw,'INEGOCIAVEL',cx,398,_PF(175))
    bw=326; bx,by=cx-bw//2,758
    draw.rounded_rectangle([bx,by,bx+bw,by+78],radius=9,fill=BLUE)
    _pctext(draw,'TEAM JE',cx,by+12,_PF(50))
    _paste_logo_post(img,h=90,pad=36)
    return img

TESTES_POSTURAL_PADRAO=[
    dict(nome='POSTURA GLOBAL',               resultado='POSITIVO', prioridade='Alta',      num_fotos=1,
         musculos='Iliopsoas, peitoral maior, esternocleidomastoideo encurtados | Gluteo maximo e abdominais fracos',
         angulos='Lordose lombar ~55-60 graus (normal 40-50) | Anteverso pelvica ~18-20 graus'),
    dict(nome='TESTE DE DORSAL',              resultado='POSITIVO', prioridade='Alta',      num_fotos=1,
         musculos='Eretores da espinha, multifidos, quadrado lombar encurtados',
         angulos='Extensao lombar excessiva durante o movimento'),
    dict(nome='TESTE DE TRENDELENBURG',       resultado='POSITIVO', prioridade='Alta',      num_fotos=2,
         musculos='Gluteo medio fraco, tensor da fascia lata, quadrado lombar em compensacao',
         angulos='Queda pelvica estimada em ~8-10 graus (alterado >5 graus)'),
    dict(nome='DISCINESE ESCAPULAR',          resultado='POSITIVO', prioridade='Media-Alta',num_fotos=2,
         musculos='Serratil anterior fraco, trapezio medio e inferior | Peitoral maior e menor encurtados',
         angulos='Assimetria escapulo-toracica visivel'),
    dict(nome='PARAVERTEBRAIS E PANTURRILHA', resultado='POSITIVO', prioridade='Media',     num_fotos=1,
         musculos='Isquiotibiais, gastrocnemio, eretores lombares encurtados',
         angulos='Dedos nao ultrapassam a linha dos pes - limitacao de ~10-15cm'),
    dict(nome='POSTERIORES DE COXA (SLR)',    resultado='POSITIVO', prioridade='Media-Alta',num_fotos=1,
         musculos='Isquiotibiais bilaterais, gastrocnemio',
         angulos='~70-75 graus alcancados (ideal >80 graus)'),
    dict(nome='ADUTORES',                     resultado='NEGATIVO', prioridade='Baixa',     num_fotos=1,
         musculos='Adutores magno, longo e curto, gracil, pectideo',
         angulos='Adequada - joelhos ~15-20cm do solo'),
    dict(nome='THOMAS',                       resultado='POSITIVO', prioridade='Alta',      num_fotos=1,
         musculos='Iliopsoas muito encurtado, reto femoral, tensor da fascia lata',
         angulos='Coxa nao repousa na maca | Joelho nao flexiona 90 graus'),
    dict(nome='AGACHAMENTO',                  resultado='POSITIVO', prioridade='Alta',      num_fotos=1,
         musculos='Quadriceps dominante, gluteos fracos e instaveis, dorsiflexores restritos',
         angulos='Valgo de joelho | Inclinacao anterior excessiva'),
    dict(nome='GLUTEO E ILIOPSOAS',           resultado='POSITIVO', prioridade='Alta',      num_fotos=1,
         musculos='Gluteo maximo fraco, gluteo medio | Iliopsoas e reto femoral encurtados',
         angulos='Padrao: Lower Crossed Syndrome - Sindrome Cruzada Inferior'),
]

def gerar_pdf_postural(dados):
    nome   = dados.get('nome','ALUNO').upper()
    numero = str(dados.get('numero','1'))
    data   = dados.get('data','--/--/----')
    testes = dados.get('testes', None)

    slides=[_post_slide_capa(nome,numero,data),_post_slide_atencao(),_post_slide_resultados()]

    testes_uso = testes if testes else [{**t,'diagnostico':f'{{DIAGNOSTICO — {t["nome"]}}}'} for t in TESTES_POSTURAL_PADRAO]

    for t in testes_uso:
        fotos=[]
        for k in ['foto_b64','foto1_b64','foto2_b64']:
            if t.get(k): fotos.append(t[k])
        slides.append(_post_slide_teste(
            nome_teste  = t.get('nome','TESTE'),
            resultado   = t.get('resultado','POSITIVO'),
            fotos_b64   = fotos or None,
            diagnostico = t.get('diagnostico',''),
            angulos     = t.get('angulos',''),
            musculos    = t.get('musculos',''),
            prioridade  = t.get('prioridade','Alta'),
            num_fotos   = t.get('num_fotos',1),
        ))
    slides.append(_post_slide_encerramento())

    PW=1920*72/150; PH=1080*72/150
    buf=_io.BytesIO()
    c=rl_canvas.Canvas(buf,pagesize=(PW,PH))
    tmp=[]
    for i,s in enumerate(slides):
        p=f'/tmp/pp_{i:03d}.jpg'; s.save(p,'JPEG',quality=95); tmp.append(p)
        c.drawImage(p,0,0,PW,PH); c.showPage()
    c.save()
    for p in tmp:
        try: os.remove(p)
        except: pass
    buf.seek(0)
    return buf

@app.route('/gerar-postural', methods=['POST'])
def gerar_postural():
    try:
        dados = request.get_json(force=True)
        if not dados: return jsonify({'error':'Dados nao enviados'}),400
        buf   = gerar_pdf_postural(dados)
        nome  = dados.get('nome','aluno').replace(' ','-').lower()
        num   = dados.get('numero','1')
        fname = f'Postural-{num}-{nome}.pdf'
        return send_file(buf,mimetype='application/pdf',as_attachment=True,download_name=fname)
    except Exception as e:
        import traceback
        return jsonify({'error':str(e),'trace':traceback.format_exc()}),500
