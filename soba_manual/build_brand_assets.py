"""Reproducible noodle-bowl icon; keep this design fixed across releases."""
from pathlib import Path
from PIL import Image, ImageDraw
from brand import GAME_TITLE, EXE_NAME, GAME_VERSION, PUBLISHER


def build():
    root=Path(__file__).parent
    assets=root/'assets';assets.mkdir(exist_ok=True)
    scale=4
    im=Image.new('RGBA',(256*scale,256*scale),(0,0,0,0))
    d=ImageDraw.Draw(im)
    def box(coords):return tuple(round(x*scale) for x in coords)
    def ellipse(coords,fill):d.ellipse(box(coords),fill=fill)
    def line(points,fill,width):d.line([(int(x*scale),int(y*scale)) for x,y in points],fill=fill,width=width*scale,joint='curve')
    d.rounded_rectangle(box((8,8,248,248)),radius=52*scale,fill='#233d32')
    # A few large shapes remain recognizable in 16px Explorer icons.
    line([(158,58),(226,27)],'#edce8e',9)
    line([(163,70),(233,40)],'#edce8e',9)
    ellipse((63,204,197,226),'#183027')
    ellipse((93,187,163,218),'#f5ddb0')
    d.pieslice(box((29,75,227,207)),start=0,end=180,fill='#c45643')
    d.polygon([(29*scale,123*scale),(227*scale,123*scale),(207*scale,172*scale),(177*scale,198*scale),(79*scale,198*scale),(49*scale,172*scale)],fill='#c45643')
    ellipse((29,82,227,155),'#fff0d1')
    ellipse((41,92,215,143),'#89532c')
    for offset in (0,14,28,42):
        d.arc(box((61+offset,98,111+offset,132)),start=0,end=330,fill='#f4d77f',width=5*scale)
    ellipse((151,99,194,130),'#fff8e8')
    ellipse((163,104,183,123),'#efb842')
    for x,y in [(65,112),(80,121),(104,105),(119,124),(144,113)]:
        d.rounded_rectangle(box((x,y,x+10,y+6)),radius=2*scale,fill='#7da35a')
    line([(57,158),(76,177),(96,185)],'#e58b66',5)
    icon=im.resize((256,256),Image.Resampling.LANCZOS)
    icon.save(assets/'game.png')
    icon.save(assets/'game.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    version_numbers=tuple(map(int,GAME_VERSION.split('.')))+(0,)
    info=f'''VSVersionInfo(ffi=FixedFileInfo(filevers={version_numbers!r},prodvers={version_numbers!r},mask=0x3f,flags=0,OS=0x40004,fileType=1,subtype=0,date=(0,0)),kids=[StringFileInfo([StringTable('040904B0',[StringStruct('FileDescription',{GAME_TITLE!r}),StringStruct('ProductName',{GAME_TITLE!r}),StringStruct('CompanyName',{PUBLISHER!r}),StringStruct('OriginalFilename',{EXE_NAME!r}),StringStruct('InternalName','QuanMiCuaToi'),StringStruct('FileVersion',{GAME_VERSION!r}),StringStruct('ProductVersion',{GAME_VERSION!r})])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])'''
    (assets/'version.txt').write_text(info,encoding='utf-8')

if __name__=='__main__':build()
