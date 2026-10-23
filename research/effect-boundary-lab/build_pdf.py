from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
import argparse
args=argparse.ArgumentParser(description='Build report PDFs; requires reportlab and DejaVu Sans fonts')
args.add_argument('--font-dir',required=True)
font_dir=Path(args.parse_args().font_dir)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('ResearchSans',str(font_dir/'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('ResearchBold',str(font_dir/'DejaVuSans-Bold.ttf')))
pdfmetrics.registerFontFamily('ResearchSans',normal='ResearchSans',bold='ResearchBold',italic='ResearchSans',boldItalic='ResearchBold')
r=Path(__file__).resolve().parent
s=getSampleStyleSheet()
s.add(ParagraphStyle(name='TitleR',fontName='ResearchBold',fontSize=22,leading=26,textColor=colors.HexColor('#25374c'),spaceAfter=16))
s.add(ParagraphStyle(name='H2R',keepWithNext=True,fontName='ResearchBold',fontSize=12,leading=16,spaceBefore=14,spaceAfter=7,textColor=colors.HexColor('#25374c')))
s.add(ParagraphStyle(name='BodyR',fontName='ResearchSans',fontSize=9.5,leading=14,spaceAfter=9,splitLongWords=True))
s.add(ParagraphStyle(name='CellR',fontName='ResearchSans',fontSize=7.5,leading=10))
s.add(ParagraphStyle(name='BriefBody',fontName='ResearchSans',fontSize=9.5,leading=13,spaceAfter=10))
def clean(t):
    return t.replace('–','-').replace('—','-').replace('×','x').replace('≥','>=').replace('’',"'")
def inline(t):
    import re
    t=escape(clean(t))
    t=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',t)
    return t

def footer(canvas,doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#ccd3dc'))
    canvas.line(48,43,547,43)
    canvas.setFont('ResearchSans',7)
    canvas.setFillColor(colors.HexColor('#52657a'))
    canvas.drawString(48,30,'VINAY MUPPALLA  /  INDEPENDENT TECHNICAL REPORT  /  v1.0')
    canvas.drawRightString(547,30,str(doc.page))
    canvas.restoreState()

def render(src,out,brief=False):
    lines=(r/src).read_text().splitlines()
    story=[]; i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:
            i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                cells=[c.strip() for c in lines[i].strip('|').split('|')]
                if not all(set(c)<=set('-: ') for c in cells):
                    rows.append([Paragraph(inline(c),s['CellR']) for c in cells])
                i+=1
            widths=[112]+[(499-112)/(len(rows[0])-1)]*(len(rows[0])-1)
            table=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7edf3')),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#cbd3dd')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
            story += [KeepTogether([story.pop(),table]),Spacer(1,12)];continue
        if line.startswith('# '):
            story.append(Paragraph(inline(line[2:]),s['TitleR']))
        elif line.startswith('## '):
            if brief and line=='## Research discussion brief':
                story.append(Paragraph('RESEARCH DISCUSSION BRIEF',s['H2R']))
            else:story.append(Paragraph(inline(line[3:]),s['H2R']))
        else:
            p=[line]
            while i+1<len(lines) and lines[i+1].strip() and not lines[i+1].startswith(('#','|')):
                i+=1;p.append(lines[i].strip())
            story.append(Paragraph(inline(' '.join(p)),s['BriefBody' if brief else 'BodyR']))
        i+=1
    doc=SimpleDocTemplate(str(r/out),pagesize=(595.28,841.89),rightMargin=48,leftMargin=48,topMargin=47,bottomMargin=57,title='Effect Boundary Lab - '+('Research Brief' if brief else 'Technical Report'),author='Vinay Muppalla')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
render('paper.md','paper.pdf')
render('brief.md','research-brief.pdf',True)
print('PDFs created')
