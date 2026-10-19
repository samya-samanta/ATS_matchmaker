import io
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import app as module

CV = 'Experienced Python SQL Flask developer with AWS and Docker skills. Builds reliable web applications.'
NOW = datetime(2026,10,19,14,0,tzinfo=timezone.utc)

def job(id, days=1, description='Python SQL Flask', **extra):
    return dict(id=id,title='Python Engineer',description=description,publication_date=(NOW-timedelta(days=days)).isoformat(),candidate_required_location='Worldwide',company_name='Example',url='https://remotive.com/remote-jobs/test/'+str(id),**extra)

class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=module.DB
        module.DB=self.tmp.name+'/test.sqlite3'
        module.app.config['TESTING']=True
        self.client=module.app.test_client()
    def tearDown(self):
        module.DB=self.old
        self.tmp.cleanup()
    def upload(self):
        return self.client.post('/api/cv',data={'cv':(io.BytesIO(CV.encode()),'resume.txt')})
    def test_upload_analyze_delete(self):
        self.assertEqual(self.upload().status_code,200)
        r=self.client.post('/api/analyze',json={'jd':'We require Python and SQL developers with Kubernetes expertise.'}).get_json()
        self.assertEqual(r['score'],67)
        self.assertEqual(r['missing'],['kubernetes'])
        self.client.delete('/api/cv')
        self.assertIsNone(self.client.get('/api/state').get_json()['cv'])
        self.assertIsNone(module.get('cv'))
        self.assertFalse(module.get('prefs')['enabled'])
    def test_strict_dates_ranking_limit(self):
        p={**module.DEFAULT,'count':2,'threshold':70}
        jobs=[job(1,16),job(2,-1),job(3,1),job(4,15),job(5,2,description='Python Java Kubernetes Rust'),job(6,3)]
        ranked=module.rank_jobs(CV,p,jobs,NOW)
        self.assertEqual([j['id'] for j in ranked],['3','6'])
        self.assertEqual(len(module.rank_jobs(CV,{**p,'count':5},jobs,NOW)),3)
    def test_location_and_title(self):
        j=job(1);j['candidate_required_location']='USA only'
        self.assertEqual(module.rank_jobs(CV,{**module.DEFAULT,'location':'India'},[j],NOW),[])
        self.assertEqual(module.rank_jobs(CV,{**module.DEFAULT,'role':'Designer'},[job(1)],NOW),[])
    def test_no_artificial_matches(self):
        self.assertEqual(module.rank_jobs('Expert copywriter and editor with ten years of experience.',module.DEFAULT,[job(1)],NOW),[])
    def test_settings_validation(self):
        for bad in [{'count':0},{'days':100},{'hour':'25:00'},{'timezone':'Bad/Zone'},{'enabled':True},[]]:
            self.assertEqual(self.client.post('/api/settings',json=bad).status_code,400)
        self.upload()
        self.assertEqual(self.client.post('/api/settings',json={**module.DEFAULT,'enabled':True}).status_code,200)
    def test_upload_validation(self):
        for name,content in [('file.exe',b'bad'),('resume.txt',b'short'),('resume.pdf',b'not a pdf')]:
            self.assertEqual(self.client.post('/api/cv',data={'cv':(io.BytesIO(content),name)}).status_code,400)
    def test_search_uses_cache_and_handles_source_failure(self):
        self.upload()
        with patch.object(module,'fetch_jobs',return_value=[job(1)]) as fetch:
            self.assertEqual(self.client.post('/api/search').status_code,200)
            self.assertEqual(self.client.post('/api/search').status_code,200)
            self.assertEqual(fetch.call_count,1)
        module.put('source_cache',{})
        with patch.object(module,'fetch_jobs',side_effect=module.requests.ConnectionError()):
            self.assertEqual(self.client.post('/api/search').status_code,502)
            self.assertIsNotNone(module.get('result'))
    def test_scheduler_est_and_once_daily(self):
        self.upload();module.put('prefs',{**module.DEFAULT,'enabled':True})
        with patch.object(module,'run_search') as search:
            module.schedule_tick(NOW-timedelta(minutes=1))
            search.assert_not_called()
            module.schedule_tick(NOW)
            module.schedule_tick(NOW+timedelta(hours=1))
            search.assert_called_once()
            module.schedule_tick(NOW+timedelta(days=1))
            self.assertEqual(search.call_count,2)
    def test_schedule_failure_visible(self):
        self.upload();module.put('prefs',{**module.DEFAULT,'enabled':True})
        with patch.object(module,'run_search',side_effect=RuntimeError()):
            module.schedule_tick(NOW)
        self.assertIn('failed',module.get('schedule_error'))
    def test_cross_origin_writes_rejected(self):
        self.assertEqual(self.client.post('/api/settings',json={},headers={'Origin':'https://other.example'}).status_code,403)

if __name__=='__main__':
    unittest.main()
