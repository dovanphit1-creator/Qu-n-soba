"""Offline notification UI test, also executed in the Windows build."""
from queue import Queue
from unittest.mock import patch
from updates import release_update, RELEASES_URL


def check_update_ui(App):
    app=App(headless=True,persistent=False)
    result=release_update({'tag_name':'v99.0.0','html_url':RELEASES_URL+'/tag/v99.0.0',
        'body':'Bổ sung món mới và sửa lỗi.','assets':[{'name':'game.exe','state':'uploaded'}]})
    assert result
    app.update_queue=Queue();app.update_queue.put(result)
    app.poll_updates()
    assert app.modal=='welcome' # Existing screens are not overwritten.
    app.action(('begin',));app.poll_updates();app.draw()
    assert app.modal=='update'
    assert {('download_update',),('dismiss',)}<=set(b[1] for b in app.buttons)
    with patch('webbrowser.open',return_value=True) as browser:
        app.action(('download_update',))
        browser.assert_called_once_with(result['url'])
    assert app.modal is None
    app.poll_updates();assert app.modal is None
    app.modal='update';app.action(('dismiss',));assert app.modal is None
