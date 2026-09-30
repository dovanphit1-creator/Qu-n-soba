"""Optional release notification. No updater executable, credentials or game data upload."""
import json
import re
from queue import Queue
from threading import Thread
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from brand import GAME_VERSION

REPOSITORY='dovanphit1-creator/Qu-n-soba'
RELEASES_URL='https://github.com/'+REPOSITORY+'/releases'
API_URL='https://api.github.com/repos/'+REPOSITORY+'/releases/latest'


def version_tuple(value):
    if not isinstance(value,str):return None
    match=re.fullmatch(r'v?(\d{1,6})\.(\d{1,6})\.(\d{1,6})',value.strip())
    return tuple(map(int,match.groups())) if match else None


def release_update(data,current=GAME_VERSION):
    if not isinstance(data,dict) or data.get('draft') or data.get('prerelease'):return None
    version=version_tuple(data.get('tag_name'))
    if version is None or version<=version_tuple(current):return None
    url=data.get('html_url','')
    if not isinstance(url,str):return None
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.netloc!='github.com' or not parsed.path.startswith('/'+REPOSITORY+'/releases/tag/') or parsed.query or parsed.fragment:return None
    assets=data.get('assets',[])
    if not isinstance(assets,list) or not any(isinstance(a,dict) and a.get('state')=='uploaded' and str(a.get('name','')).lower().endswith(('.exe','.zip')) for a in assets):return None
    body=data.get('body') or 'Xem chi tiết thay đổi trên trang phát hành.'
    if not isinstance(body,str):body='Xem chi tiết thay đổi trên trang phát hành.'
    body=' '.join(body.split())
    body=''.join(c for c in body if c.isprintable())
    if len(body)>420:body=body[:417]+'…'
    return {'version':data['tag_name'],'url':url,'notes':body}


def fetch_update(opener=urlopen):
    request=Request(API_URL,headers={'Accept':'application/vnd.github+json','User-Agent':'QuanMiCuaToi/'+GAME_VERSION})
    try:
        with opener(request,timeout=5) as response:
            raw=response.read(262145)
        if len(raw)>262144:return None
        return release_update(json.loads(raw.decode('utf-8')))
    except Exception:
        # Offline, timeout, rate limits and invalid releases must not prevent play.
        return None


def start_check():
    results=Queue(maxsize=1)
    Thread(target=lambda:results.put(fetch_update()),name='release-check',daemon=True).start()
    return results
