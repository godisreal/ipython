# coding: utf-8
import io
import json
import os
from os.path import join as pjoin
import shutil

import requests

from IPython.html.utils import url_path_join
from IPython.html.tests.launchnotebook import NotebookTestBase, assert_http_error
from IPython.nbformat.current import (new_notebook, write, new_worksheet,
                                      new_heading_cell, new_code_cell,
                                      new_output)

class NbconvertAPI(object):
    """Wrapper for nbconvert API calls."""
    def __init__(self, base_url):
        self.base_url = base_url

    def _req(self, verb, path, body=None, params=None):
        response = requests.request(verb,
                url_path_join(self.base_url, 'nbconvert', path),
                data=body, params=params,
        )
        response.raise_for_status()
        return response

    def from_file(self, format, path, name, download=False):
        return self._req('GET', url_path_join(format, path, name),
                         params={'download':download})

    def from_post(self, format, nbmodel):
        body = json.dumps(nbmodel)
        return self._req('POST', format, body)

    def list_formats(self):
        return self._req('GET', '')

class APITest(NotebookTestBase):
    def setUp(self):
        nbdir = self.notebook_dir.name
        
        if not os.path.isdir(pjoin(nbdir, 'foo')):
            os.mkdir(pjoin(nbdir, 'foo'))
        
        nb = new_notebook(name='testnb')
        
        ws = new_worksheet()
        nb.worksheets = [ws]
        ws.cells.append(new_heading_cell(u'Created by test ³'))
        cc1 = new_code_cell(input=u'print(2*6)')
        cc1.outputs.append(new_output(output_text=u'12'))
        ws.cells.append(cc1)
        
        with io.open(pjoin(nbdir, 'foo', 'testnb.ipynb'), 'w',
                     encoding='utf-8') as f:
            write(nb, f, format='ipynb')

        self.nbconvert_api = NbconvertAPI(self.base_url())

    def tearDown(self):
        nbdir = self.notebook_dir.name

        for dname in ['foo']:
            shutil.rmtree(pjoin(nbdir, dname), ignore_errors=True)
    
    def test_from_file(self):
        r = self.nbconvert_api.from_file('html', 'foo', 'testnb.ipynb')
        self.assertEqual(r.status_code, 200)
        self.assertIn(u'text/html', r.headers['Content-Type'])
        self.assertIn(u'Created by test', r.text)
        self.assertIn(u'print', r.text)

        r = self.nbconvert_api.from_file('python', 'foo', 'testnb.ipynb')
        self.assertIn(u'text/x-python', r.headers['Content-Type'])
        self.assertIn(u'print(2*6)', r.text)

    def test_from_file_404(self):
        with assert_http_error(404):
            self.nbconvert_api.from_file('html', 'foo', 'thisdoesntexist.ipynb')

    def test_from_file_download(self):
        r = self.nbconvert_api.from_file('python', 'foo', 'testnb.ipynb', download=True)
        content_disposition = r.headers['Content-Disposition']
        self.assertIn('attachment', content_disposition)
        self.assertIn('testnb.py', content_disposition)

    def test_from_file_zip(self):
        r = self.nbconvert_api.from_file('latex', 'foo', 'testnb.ipynb', download=True)
        self.assertIn(u'application/zip', r.headers['Content-Type'])
        self.assertIn(u'.zip', r.headers['Content-Disposition'])

    def test_from_post(self):
        nbmodel_url = url_path_join(self.base_url(), 'api/notebooks/foo/testnb.ipynb')
        nbmodel = requests.get(nbmodel_url).json()
        
        r = self.nbconvert_api.from_post(format='html', nbmodel=nbmodel)
        self.assertEqual(r.status_code, 200)
        self.assertIn(u'text/html', r.headers['Content-Type'])
        self.assertIn(u'Created by test', r.text)
        self.assertIn(u'print', r.text)
        
        r = self.nbconvert_api.from_post(format='python', nbmodel=nbmodel)
        self.assertIn(u'text/x-python', r.headers['Content-Type'])
        self.assertIn(u'print(2*6)', r.text)

    def test_from_post_zip(self):
        nbmodel_url = url_path_join(self.base_url(), 'api/notebooks/foo/testnb.ipynb')
        nbmodel = requests.get(nbmodel_url).json()

        r = self.nbconvert_api.from_post(format='latex', nbmodel=nbmodel)
        self.assertIn(u'application/zip', r.headers['Content-Type'])
        self.assertIn(u'.zip', r.headers['Content-Disposition'])
