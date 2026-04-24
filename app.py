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
