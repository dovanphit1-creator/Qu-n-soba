import io,json,unittest
from updates import release_update,fetch_update,RELEASES_URL

class UpdateTests(unittest.TestCase):
    def release(self,**changes):
        data={'tag_name':'v1.3.0','html_url':RELEASES_URL+'/tag/v1.3.0','body':'Sửa lỗi','draft':False,'prerelease':False,'assets':[{'name':'QuanMi.exe','state':'uploaded'}]}
        data.update(changes);return data
    def test_numeric_versions_and_current(self):
        self.assertTrue(release_update(self.release(tag_name='v1.10.0'),'1.9.0'))
        for v in ['1.0.2','v1.0.1','v1.2.0-beta','not-a-version']:
            self.assertIsNone(release_update(self.release(tag_name=v),'1.0.2'))
    def test_only_published_downloadable_releases(self):
        for changes in [{'draft':True},{'prerelease':True},{'assets':[]},{'assets':[{'name':'source.tar.gz','state':'uploaded'}]}]:
            self.assertIsNone(release_update(self.release(**changes)))
    def test_repository_urls_only(self):
        for url in ['https://evil.test/download','https://github.com.evil.test/x','file:///tmp/game.exe','https://github.com/other/repo/releases/tag/v2.0.0']:
            self.assertIsNone(release_update(self.release(html_url=url)))
    def test_offline_timeout_invalid_response(self):
        def offline(*a,**k):raise TimeoutError()
        self.assertIsNone(fetch_update(offline))
        for raw in [b'invalid',b'x'*262145,b'[]']:
            self.assertIsNone(fetch_update(lambda *a,**k:io.BytesIO(raw)))
    def test_bounded_notes_and_request_timeout(self):
        def response(request,timeout):
            self.assertEqual(timeout,5)
            self.assertEqual(request.get_method(),'GET')
            return io.BytesIO(json.dumps(self.release(body='a'*1000)).encode())
        self.assertLessEqual(len(fetch_update(response)['notes']),420)
if __name__=='__main__':unittest.main()
