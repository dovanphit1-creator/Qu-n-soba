"""Windows tray, per-user singleton and graceful installer shutdown IPC."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
from queue import Queue, Empty
import sys
import threading
from model import save_path

_mutex=None

def request_path(kind):return save_path().parent/(kind+'-request.json')

def single_instance():
    global _mutex
    if sys.platform!='win32':return True
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[wintypes.LPVOID,wintypes.BOOL,wintypes.LPCWSTR]
    kernel.CreateMutexW.restype=wintypes.HANDLE
    _mutex=kernel.CreateMutexW(None,False,'Local\\QuanMiCuaToi-'+os.environ.get('USERNAME','player'))
    if not _mutex:raise OSError(ctypes.get_last_error(),'Could not create game mutex')
    exists=ctypes.get_last_error()==183
    if exists:
        import json,time
        p=request_path('show');p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps({'at':time.time()}),encoding='utf-8')
    else:
        for kind in ('show','shutdown'):
            request_path(kind).unlink(missing_ok=True)
    return not exists


class Background:
    def __init__(self,app):
        self.app=app;self.hidden=False;self.icon=None;self.queue=Queue();self.ready=threading.Event()
        import pygame as pg
        self.hwnd=pg.display.get_wm_info()['window']
        self.user=ctypes.WinDLL('user32',use_last_error=True)
        self.user.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
        self.user.SetForegroundWindow.argtypes=[wintypes.HWND]

    def enable(self,enabled):
        if enabled:
            if self.icon is None:
                try:
                    import pystray
                    from PIL import Image
                    from brand import GAME_TITLE
                    self.ready.clear()
                    self.icon=pystray.Icon('QuanMiCuaToi',Image.open(Path(__file__).with_name('assets')/'game.png'),GAME_TITLE,
                        menu=pystray.Menu(pystray.MenuItem('Mở game',lambda icon,item:self.queue.put('show'),default=True),
                                          pystray.MenuItem('Lưu và thoát hoàn toàn',lambda icon,item:self.queue.put('quit'))))
                    def setup(icon):icon.visible=True;self.ready.set()
                    def run():
                        try:self.icon.run(setup=setup)
                        except Exception:self.queue.put('tray_failed')
                    threading.Thread(target=run,daemon=True).start()
                    if not self.ready.wait(3):
                        self.stop();return False
                except (ImportError,OSError):self.stop();return False
            self.startup(True)
        else:
            self.show();self.stop();self.startup(False)
        return True

    def startup(self,enabled):
        import winreg
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
                if enabled:
                    command='"'+sys.executable+'" --background' if getattr(sys,'frozen',False) else '"'+sys.executable+'" "'+str(Path(__file__).with_name('main.py'))+'" --background'
                    winreg.SetValueEx(key,'QuanMiCuaToi',0,winreg.REG_SZ,command)
                else:
                    try:winreg.DeleteValue(key,'QuanMiCuaToi')
                    except FileNotFoundError:pass
        except OSError:self.app.last_warning='Không đặt được tự khởi động cùng Windows. Chạy nền vẫn dùng được trong lần chơi này.'

    def hide(self):
        if self.icon is None:return
        self.user.ShowWindow(self.hwnd,0);self.hidden=True
        try:self.icon.notify('Nhân viên tiếp tục làm đúng ca khi máy còn bật.','Quán Mì Của Tôi đang chạy nền')
        except Exception:pass

    def show(self):
        self.user.ShowWindow(self.hwnd,9);self.user.SetForegroundWindow(self.hwnd);self.hidden=False

    def poll(self):
        import json,time
        for kind in ('shutdown','show'):
            p=request_path(kind)
            if p.exists():
                try:
                    data=json.loads(p.read_text(encoding='utf-8-sig'))
                    if time.time()-data.get('at',0)<60 and (kind=='show' or os.path.normcase(data.get('exe',''))==os.path.normcase(sys.executable)):
                        self.queue.put('quit' if kind=='shutdown' else 'show')
                    p.unlink(missing_ok=True)
                except (OSError,ValueError):pass
        while True:
            try:kind=self.queue.get_nowait()
            except Empty:break
            if kind=='quit':self.app.action(('quit',))
            elif kind=='show':self.show()
            elif kind=='tray_failed':
                self.show();self.app.world.background_enabled=False;self.startup(False)
                self.app.last_warning='Khay hệ thống không hoạt động; đã tắt chế độ nền.'

    def stop(self):
        if self.icon is not None:
            icon=self.icon;self.icon=None
            try:icon.stop()
            except Exception:pass
