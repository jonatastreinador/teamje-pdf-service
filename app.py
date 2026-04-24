"""
TEAMJE PDF Service — Gera PDFs profissionais de Dieta e Avaliação Postural
Deploy: Render.com (gratuito)
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import io, base64, os, tempfile

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, Image as RLImage)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

from logo_data import LOGO_B64, WM_B64

app = Flask(__name__)
CORS(app)  # Permite chamadas do Vercel

W, H = A4
PRETO   = colors.HexColor('#0D0D0D')
CINZA_L = colors.HexColor('#F4F4F4')
CINZA_B = colors.HexColor('#E0E0E0')
CINZA_T = colors.HexColor('#444444')
BRANCO  = colors.white

# ── Salva logos em disco temporário ──────────────────────────────────
def get_logo_path():
    tmp = tempfile.gettempdir()
    logo = os.path.join(tmp, 'teamje_logo.png')
    wm   = os.path.join(tmp, 'teamje_wm.png')
    if not os.path.exists(logo):
        with open(logo, 'wb') as f:
            f.write(base64.b64decode(LOGO_B64))
    if not os.path.exists(wm):
        with open(wm, 'wb') as f:
            f.write(base64.b64decode(WM_B64))
    return logo, wm

# ── Background (logo + watermark) ────────────────────────────────────
class BG:
    def __init__(self, logo, wm):
        self.logo = logo
        self.wm   = wm

    def __call__(self, canv, doc):
        canv.saveState()
        canv.setFillColor(BRANCO)
        canv.rect(0, 0, W, H, fill=1, stroke=0)
        # Watermark full page
        canv.drawImage(self.wm, 0, 0, W, H,
                       preserveAspectRatio=False, mask='auto')
        # Logo top-right
        canv.drawImage(self.logo, W-4.6*cm, H-1.6*cm, 4.1*cm, 1.3*cm,
                       preserveAspectRatio=True, mask='auto')
        # Logo footer center
        canv.drawImage(self.logo, W/2-2.3*cm, 0.2*cm, 4.6*cm, 1.5*cm,
                       preserveAspectRatio=True, mask='auto')
        canv.restoreState()

def S(name, **kw):
    base = dict(fontName='Helvetica', fontSize=9.5, textColor=PRETO, leading=13, spaceAfter=3)
    base.update(kw)
    return ParagraphStyle(name, **base)

def banner(t1, t2=''):
    rows = [[Paragraph(f'<b>{t1}</b>',
        S('b1', fontName='Helvetica-Bold', fontSize=13, textColor=BRANCO,
          alignment=TA_CENTER, leading=18))]]
    if t2:
        rows.append([Paragraph(f'<b>{t2}</b>',
            S('b2', fontName='Helvetica-Bold', fontSize=10, textColor=BRANCO,
              alignment=TA_CENTER, leading=14))])
    t = Table(rows, colWidths=[W-3.6*cm])
    t.setStyle(TableStyle([('BACKGROUND', (0,0),(-1,-1), PRETO),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
    return t

def pill(label):
    p = Paragraph(f'<b>{label}</b>',
        S('pl', fontName='Helvetica-Bold', fontSize=11, textColor=BRANCO,
          alignment=TA_CENTER, leading=16))
    inn = Table([[p]], colWidths=[7.5*cm])
    inn.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PRETO),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('LEFTPADDING',(0,0),(-1,-1),20),('RIGHTPADDING',(0,0),(-1,-1),20),
        ('ROUNDEDCORNERS',[20])]))
    out = Table([[inn]], colWidths=[W-3.6*cm])
    out.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER')]))
    return out

def mtbl(rows_data, av=''):
    hdr = [
        Paragraph('<b>Categoria</b>', S('th', fontName='Helvetica-Bold', fontSize=9, textColor=BRANCO, alignment=TA_CENTER)),
        Paragraph('<b>Opções</b>',    S('th2',fontName='Helvetica-Bold', fontSize=9, textColor=BRANCO, alignment=TA_CENTER)),
    ]
    data = [hdr]
    for cat, opts in rows_data:
        data.append([
            Paragraph(f'<b>{cat}</b>', S('cat', fontName='Helvetica-Bold', fontSize=9, textColor=PRETO, alignment=TA_CENTER, leading=12)),
            Paragraph(opts, S('opt', fontSize=9, textColor=PRETO, alignment=TA_CENTER, leading=12)),
        ])
    if av:
        data.append([
            Paragraph('<b>À-vontade</b>', S('avc', fontName='Helvetica-Bold', fontSize=9, textColor=PRETO, alignment=TA_CENTER, leading=12)),
            Paragraph(av, S('avo', fontSize=9, textColor=PRETO, alignment=TA_CENTER, leading=12)),
        ])
    t = Table(data, colWidths=[3.2*cm, 13.3*cm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),PRETO), ('TEXTCOLOR',(0,0),(-1,0),BRANCO),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),  ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'), ('FONTSIZE',(0,0),(-1,-1),9),
        ('GRID',(0,0),(-1,-1),0.4,CINZA_B),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
    ] + [('BACKGROUND',(0,i),(-1,i),CINZA_L) for i in range(2,len(data),2)]))
    return t

# ════════════════════════════════════════════════════════════════════
# GERAR PDF DIETA
# ════════════════════════════════════════════════════════════════════
def gerar_pdf_dieta(dados):
    logo, wm = get_logo_path()
    bg = BG(logo, wm)

    nome = dados.get('nome','ALUNO').upper()
    num  = dados.get('numero','1')
    data = dados.get('data','—')
    kcal = dados.get('kcal','2000')

    def parse_refeicao(key):
        r = dados.get(key, [])
        if isinstance(r, list):
            return [(item['categoria'], item['opcoes']) for item in r]
        return []

    cafe     = parse_refeicao('cafe_manha')
    almoco   = parse_refeicao('almoco')
    almoco_av= dados.get('almoco_avontade','Alface, tomate, pepino, repolho, brócolis, cenoura, abobrinha, vagem, couve-flor')
    lanche   = parse_refeicao('lanche_tarde')
    jantar   = parse_refeicao('jantar')
    jantar_av= dados.get('jantar_avontade','Alface, tomate, pepino, repolho, brócolis, cenoura, abobrinha, vagem, couve-flor')
    supls    = dados.get('suplementos',[])
    rec_c    = dados.get('rec_cardio','Incorpore cardio de 5 a 7 vezes por semana, 30 minutos por dia.')
    rec_a    = dados.get('rec_agua','35 ml por kg de peso corporal ao dia.')
    rec_m    = dados.get('rec_musculacao','Treine de 4 a 5 vezes por semana, priorizando musculação.')
    rec_d    = dados.get('rec_dicas',[])

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.8*cm, bottomMargin=2.6*cm)
    st = []

    # ══ PÁG 1: Header + Café + Almoço ══════════════════════════════
    tit = Paragraph(f'<b>PROTOCOLO DIETÉTICO {num}: {nome}</b>',
        S('ht', fontName='Helvetica-Bold', fontSize=14, textColor=PRETO, leading=18))
    sub = Paragraph(f'DATA {data}&nbsp;&nbsp;&nbsp;&nbsp;{kcal}kcal',
        S('hs', fontSize=10, textColor=CINZA_T, leading=14))
    hdr = Table([[tit,''],[sub,'']], colWidths=[13.0*cm,2.8*cm])
    hdr.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LINEBELOW',(0,1),(-1,1),2,PRETO),('BOTTOMPADDING',(0,1),(-1,1),6)]))
    st.append(hdr); st.append(Spacer(1,8))
    st.append(banner('REFEIÇÕES')); st.append(Spacer(1,8))

    for txt in ['PASSO-A-PASSO PARA MONTAR REFEIÇÕES:',
                'ESCOLHA UMA OPÇÃO DE CADA CATEGORIA PARA CADA REFEIÇÃO.']:
        st.append(Paragraph(f'<b>{txt}</b>',
            S('pp',fontName='Helvetica-Bold',fontSize=9.5,textColor=PRETO,alignment=TA_CENTER,leading=14)))
    st.append(Spacer(1,4))
    for lbl in ['Carboidrato','Proteína','Gordura','Fruta']:
        rest = ': Escolha uma opção' + (' ou mais respeitando as 150g' if lbl=='Fruta' else '')
        st.append(Paragraph(f'<b><font color="#1565C0">{lbl}:</font></b>{rest}',
            S('pc',fontSize=9.5,alignment=TA_CENTER,leading=13)))
    st.append(Spacer(1,10))

    if cafe:
        st.append(pill('CAFÉ DA MANHÃ')); st.append(Spacer(1,6))
        st.append(mtbl(cafe)); st.append(Spacer(1,12))
    if almoco:
        st.append(pill('ALMOÇO')); st.append(Spacer(1,6))
        st.append(mtbl(almoco, almoco_av))
    st.append(PageBreak())

    # ══ PÁG 2: Lanche + Jantar ══════════════════════════════════════
    st.append(Spacer(1,4))
    if lanche:
        st.append(pill('LANCHE DA TARDE')); st.append(Spacer(1,6))
        st.append(mtbl(lanche)); st.append(Spacer(1,14))
    if jantar:
        st.append(pill('JANTAR')); st.append(Spacer(1,6))
        st.append(mtbl(jantar, jantar_av))
    st.append(PageBreak())

    # ══ PÁG 3: Recomendações + Refeição Livre ══════════════════════
    st.append(banner('RECOMENDAÇÕES')); st.append(Spacer(1,10))
    for b,tx in [('CARDIO: SEMPRE BEM-VINDO!',rec_c),
                 ('ÁGUA É VIDA: ADOTE UMA GARRAFA!',rec_a),
                 ('MUSCULAÇÃO: FOCO NO TREINO!',rec_m)]:
        st.append(Paragraph(f'<b>{b}</b> {tx}',
            S('ri',fontSize=9.5,textColor=PRETO,leading=14,spaceAfter=7,alignment=TA_JUSTIFY)))
    if rec_d:
        st.append(Paragraph('<b>DICAS ESSENCIAIS:</b>',
            S('dk',fontName='Helvetica-Bold',fontSize=9.5,textColor=PRETO,spaceAfter=3)))
        for d in rec_d:
            st.append(Paragraph(f'✔ {d}',
                S('di',fontSize=9.5,textColor=PRETO,leading=13,leftIndent=10,spaceAfter=3)))
    st.append(Spacer(1,14))
    st.append(banner('REFEIÇÃO LIVRE','CORRETAMENTE')); st.append(Spacer(1,10))
    for tx in [
        'Se você acha que dieta é sinônimo de sofrimento ou que precisa viver à base de frango e batata-doce para ter resultado… respira.',
        'A refeição livre existe justamente para quebrar essa ideia. Ela é uma ferramenta estratégica — e não uma desculpa para exagerar. Quando usada com consciência, pode melhorar sua adesão, controlar a ansiedade e até acelerar seus resultados por ajudar no equilíbrio psicológico.',
    ]:
        st.append(Paragraph(tx, S('rl',fontSize=9.5,textColor=PRETO,leading=14,spaceAfter=7,alignment=TA_JUSTIFY)))
    st.append(PageBreak())

    # ══ PÁG 4: Refeição Livre detalhada ════════════════════════════
    st.append(banner('REFEIÇÃO LIVRE','CORRETAMENTE')); st.append(Spacer(1,10))
    for bold,items in [
        ('O QUE É UMA REFEIÇÃO LIVRE?',['É uma ou duas refeições na semana em que você pode comer algo fora do seu plano alimentar, sem se preocupar com pesar alimentos, contar macros ou seguir uma estrutura rígida. Mas atenção: "livre" não é sinônimo de "descontrolado".']),
        ('QUANDO FAZER?',['● 1 vez por semana','● Substituindo até 2 refeições da sua dieta no mesmo dia']),
        ('Exemplo:',['● Almoço com sua família (churrasco, feijoada, etc.)','● Jantar com amigos (hambúrguer, pizza, etc.)']),
        ('OBJETIVOS DA REFEIÇÃO LIVRE:',['● Reduzir ansiedade e compulsão','● Melhorar a adesão ao plano alimentar','● Aumentar momentaneamente a leptina (hormônio que regula fome e gasto energético)','● Recuperar energia física e mental','● Tornar o processo mais leve e sustentável']),
        ('CUIDADOS IMPORTANTES',['● Evite transformar a refeição livre em um dia inteiro de exageros.','● Não compense no dia seguinte com jejum ou restrições extremas.','● Evite alimentos que te causam desconforto ou alergias.','● Cuidado com o álcool em excesso — ele pode atrapalhar sua recuperação, sono e retenção hídrica.']),
    ]:
        st.append(Paragraph(f'<b>{bold}</b>',S('h4',fontName='Helvetica-Bold',fontSize=9.5,textColor=PRETO,spaceAfter=2)))
        for it in items:
            st.append(Paragraph(it,S('l4',fontSize=9.5,textColor=PRETO,leading=13,leftIndent=8,spaceAfter=2,alignment=TA_JUSTIFY)))
        st.append(Spacer(1,4))
    st.append(PageBreak())

    # ══ PÁG 5: Refeição Livre cont. ════════════════════════════════
    st.append(banner('REFEIÇÃO LIVRE','CORRETAMENTE')); st.append(Spacer(1,10))
    for bold,items in [
        ('DICAS PARA FAZER DA FORMA CERTA',['● Planeje com antecedência o dia e a refeição','● Aproveite o momento com prazer, mas com consciência','● Coma devagar, mastigue bem e observe os sinais de saciedade','● Se possível, inclua alimentos que você gosta MUITO — isso reforça a sensação de liberdade']),
        ('RESUMO PRÁTICO',['● Frequência: 1x na semana','● Quantidade: até 2 refeições do dia','● Regra de ouro: Aproveite, mas não exagere!']),
    ]:
        st.append(Paragraph(f'<b>{bold}</b>',S('h5',fontName='Helvetica-Bold',fontSize=9.5,textColor=PRETO,spaceAfter=2)))
        for it in items:
            st.append(Paragraph(it,S('l5',fontSize=9.5,textColor=PRETO,leading=13,leftIndent=8,spaceAfter=2)))
        st.append(Spacer(1,6))
    st.append(Paragraph('Lembre-se: o equilíbrio é o que faz uma dieta funcionar no longo prazo. Você não precisa ser perfeito, só precisa ser consistente.',S('lm',fontSize=9.5,textColor=PRETO,leading=14,spaceAfter=8,alignment=TA_JUSTIFY)))
    st.append(Paragraph('<b>CONSIDERAÇÕES FINAIS</b>',S('cf',fontName='Helvetica-Bold',fontSize=9.5,textColor=PRETO,spaceAfter=2)))
    st.append(Paragraph('A refeição livre existe para você seguir firme na sua jornada — não como fuga, mas como estratégia. Se usada com maturidade, ela ajuda a manter o plano de forma leve, prazerosa e sem culpa.',S('cfb',fontSize=9.5,textColor=PRETO,leading=14,spaceAfter=6,alignment=TA_JUSTIFY)))
    st.append(Paragraph('Agora que você sabe como funciona, use com sabedoria e continue evoluindo no seu processo!',S('cfb2',fontSize=9.5,textColor=PRETO,leading=14,alignment=TA_JUSTIFY)))
    st.append(PageBreak())

    # ══ PÁG 6: Suplementos ═════════════════════════════════════════
    st.append(banner('SUPLEMENTOS','BÁSICOS')); st.append(Spacer(1,14))
    for sup in supls:
        nd = sup.get('nome','')
        hr = sup.get('horario','')
        jf = sup.get('justificativa','')
        st.append(Paragraph(f'<b>{nd}</b> ➡ {hr}',
            S('sn',fontName='Helvetica-Bold',fontSize=9.5,textColor=PRETO,leading=13,spaceAfter=1)))
        st.append(Paragraph(f'Por quê? {jf}',
            S('sj',fontSize=9,textColor=CINZA_T,leading=13,spaceAfter=9,alignment=TA_JUSTIFY)))
    st.append(PageBreak())

    # ══ PÁG 7: Higiene do Sono ═════════════════════════════════════
    st.append(banner('HIGIENE DO SONO')); st.append(Spacer(1,10))
    st.append(Paragraph('Uma noite mal dormida não apenas prejudicará o crescimento muscular ou o emagrecimento, mas também estimulará o catabolismo, ou seja, a perda de massa muscular. Para assegurar a recuperação muscular, é fundamental desfrutar de uma noite de sono adequada.',S('so',fontSize=9.5,textColor=PRETO,leading=14,spaceAfter=10,alignment=TA_JUSTIFY)))
    for tit,desc,dica in [
        ('USE CHÁS RELAXANTES ANTES DE DORMIR','Ervas como passiflora, mulungu e melissa têm propriedades calmantes que favorecem o relaxamento.','Evite chás com cafeína. Tome o chá cerca de 30 minutos antes de dormir.'),
        ('AROMATIZE O AMBIENTE COM ÓLEOS ESSENCIAIS','Aromas suaves como lavanda e laranja doce podem reduzir a tensão e criar um clima mais propício ao sono.','Utilize difusores ou velas aromáticas seguras, especialmente formuladas para uso noturno.'),
        ('EVITE ESTIMULANTES APÓS AS 18H','Substâncias como cafeína (café, chá-preto, refrigerantes) e nicotina podem interferir no ciclo natural do sono.','Fique atento também a medicamentos e suplementos que contenham cafeína.'),
        ('CRIE UM RITUAL DE RELAXAMENTO ANTES DE DORMIR','Técnicas como respiração profunda, leitura leve ou meditação guiada ajudam a desacelerar corpo e mente.','Crie uma rotina simples e repita todos os dias — o cérebro responde bem a rituais consistentes.'),
        ('REDUZA A EXPOSIÇÃO A LUZES FORTES À NOITE','Ambientes muito iluminados dificultam a produção de melatonina.',''),
    ]:
        st.append(Paragraph(f'<b>{tit}</b> <font color="#555555">Por que:</font> {desc}',S('si',fontSize=9.5,textColor=PRETO,leading=14,spaceAfter=2,alignment=TA_JUSTIFY)))
        if dica:
            st.append(Paragraph(f'<b>Dica:</b> {dica}',S('sd',fontSize=9.5,textColor=PRETO,leading=13,leftIndent=10,spaceAfter=6)))
        else:
            st.append(Spacer(1,6))
    st.append(Paragraph('<b>DICA EXTRA:</b> Garanta um ambiente favorável ao sono: ● Quarto escuro, silencioso e fresco ● Horários regulares para dormir e acordar — inclusive aos fins de semana ● Evite usar o quarto para trabalhar ou estudar — associe-o ao descanso',S('de',fontSize=9.5,textColor=PRETO,leading=14,alignment=TA_JUSTIFY)))

    doc.build(st, onFirstPage=bg, onLaterPages=bg)
    buf.seek(0)
    return buf

# ════════════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════════════
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'TEAMJE PDF Service'})

@app.route('/gerar-dieta', methods=['POST'])
def gerar_dieta():
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'error': 'Dados não enviados'}), 400

        buf = gerar_pdf_dieta(dados)
        nome  = dados.get('nome','aluno').replace(' ','-').lower()
        num   = dados.get('numero','1')
        fname = f'Dieta-{num}-{nome}.pdf'

        return send_file(buf, mimetype='application/pdf',
                         as_attachment=True, download_name=fname)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'service': 'TEAMJE PDF Service',
        'version': '1.0',
        'endpoints': {
            'GET  /health':        'Status do serviço',
            'POST /gerar-dieta':   'Gerar PDF de dieta',
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
