"""Use the same restaurant painting and branded layout in the native EXE splash."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from brand import GAME_TITLE, GAME_VERSION, PUBLISHER

def build():
    root=Path(__file__).parent
    art=Image.open(root/'loading-art/restaurant.jpg').convert('RGBA').resize((1280,720),Image.Resampling.LANCZOS)
    shade=Image.new('RGBA',art.size)
    paint=ImageDraw.Draw(shade)
    for x in range(1280):
        alpha=round(220-180*min(1,x/1100))
        paint.line((x,0,x,720),fill=(11,25,19,alpha))
    art=Image.alpha_composite(art,shade)
    draw=ImageDraw.Draw(art)
    def font(size,bold=False):
        candidates=[Path('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
        return ImageFont.truetype(str(next(p for p in candidates if p.exists())),size)
    icon=Image.open(root/'assets/game.png').convert('RGBA').resize((58,58),Image.Resampling.LANCZOS)
    art.alpha_composite(icon,(64,125))
    draw.text((64,205),'MỜI BẠN GHÉ QUÁN',font=font(13,True),fill='#e5cda3')
    draw.text((60,235),'Quán Mì',font=font(64,True),fill='#fff4df')
    draw.text((60,310),'Của Tôi',font=font(64,True),fill='#fff4df')
    draw.text((64,408),'Một quán nhỏ. Từng bát mì.',font=font(21),fill='#f0dcc0')
    draw.text((64,444),'Câu chuyện của bạn.',font=font(21),fill='#f0dcc0')
    draw.rounded_rectangle((64,503,404,506),radius=2,fill='#e9b879')
    draw.text((64,527),'Đang chuẩn bị quán…',font=font(16),fill='#fff4df')
    draw.text((64,610),f'Phiên bản {GAME_VERSION} · Nhà phát hành {PUBLISHER}',font=font(12),fill='#c6baa6')
    art.convert('RGB').save(root/'assets/loading-windows.png',optimize=True)

if __name__=='__main__':build()
