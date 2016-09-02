from __future__ import absolute_import, print_function, unicode_literals
import sys
import requests
import json
import re
from bs4 import BeautifulSoup
from pandas.io.json import json_normalize
if sys.version_info[0] == 2:  # Python 2
    from urllib import quote
else:  # Python 3
    from urllib.parse import quote


class trendReq(object):
    """
    Google Trends API
    """
    def __init__(self, username, password, custom_useragent=None):
        """
        Initialize hard-coded URLs, HTTP headers, and login parameters
        needed to connect to Google Trends, then connect.
        """
        self.username = username
        self.password = password
        self.url_login = "https://accounts.google.com/ServiceLogin"
        self.url_auth = "https://accounts.google.com/ServiceLoginAuth"
        # custom user agent so users know what "new account signin for Google" is
        if custom_useragent is None:
            self.custom_useragent = {'User-Agent': 'Pytrends'}
        else:
            self.custom_useragent = custom_useragent
        self._connect()
        self.results = None
        self.result_df = None

    def _connect(self):
        """
        Connect to Google.
        Go to login page GALX hidden input value and send it back to google + login and password.
        http://stackoverflow.com/questions/6754709/logging-in-to-google-using-python
        """
        self.ses = requests.session()
        login_html = self.ses.get(self.url_login, headers=self.custom_useragent)
        soup_login = BeautifulSoup(login_html.content, "lxml").find('form').find_all('input')
        dico = {}
        for u in soup_login:
            if u.has_attr('value'):
                dico[u['name']] = u['value']
        # override the inputs with out login and pwd:
        dico['Email'] = self.username
        dico['Passwd'] = self.password
        self.ses.post(self.url_auth, data=dico)

    def trend(self, payload):
        payload['cid'] = 'TIMESERIES_GRAPH_0'
        payload['export'] = 3
        req_url = "http://www.google.com/trends/fetchComponent"
        req = self.ses.get(req_url, params=payload)
        self._trend_helper(req.text)

    def _trend_helper(self, raw_text):
        # strip off js function call 'google.visualization.Query.setResponse();
        text = raw_text[62:-2]
        # replace series of commas ',,,,'
        text = text.replace(',,,,', '')
        # replace js new Date(YYYY, M, 1) calls with ISO 8601 date as string
        pattern = re.compile(r'new Date\(\d{4},\d{1,2},1\)')
        for match in re.finditer(pattern, text):
            # slice off 'new Date(' and ')' and split by comma
            csv_date = match.group(0)[9:-1].split(',')
            year = csv_date[0]
            month = csv_date[1].zfill(2)
            # covert into "YYYY-MM-DD" including quotes
            str_dt = '"' + year + '-' + month + '-01"'
            text = text.replace(match.group(0), str_dt)
        self.results = json.loads(text)

    def toprelated(self, payload):
        payload['cid'] = 'RISING_QUERIES_0_0'
        payload['export'] = 3
        if 'hl' not in payload:
            payload['hl'] = 'en-US'
        req_url = "http://www.google.com/trends/fetchComponent"
        req = self.ses.get(req_url, params=payload)
        # strip off google.visualization.Query.setResponse();
        raw_text = req.text[62:-2]
        self.results = json.loads(raw_text)

    def top30in30(self):
        form = {'ajax': '1', 'pn': 'p1', 'htv': 'm'}
        req_url = "http://www.google.com/trends/hottrends/hotItems"
        req = self.ses.post(req_url, data=form)
        self.results = req.json()

    def hottrends(self, payload):
        req_url = "http://hawttrends.appspot.com/api/terms/"
        req = self.ses.get(req_url, params=payload)
        self.results = req.json()

    def hottrendsdetail(self, payload):
        req_url = "http://www.google.com/trends/hottrends/atom/feed"
        req = self.ses.get(req_url, params=payload)
        # TODO need to convert rss feed to json
        self.results = req.json()

    def topcharts(self, form):
        form['ajax'] = '1'
        req_url = "http://www.google.com/trends/topcharts/category"
        req = self.ses.post(req_url, data=form)
        self.results = req.json()

    def suggestions(self, keyword):
        kw_param = quote(keyword)
        req = requests.get("https://www.google.com/trends/api/autocomplete/" + kw_param)
        # response is invalid json but if you strip off ")]}'," from the front it is then valid
        json_data = json.loads(req.text[5:])
        self.results = json_data

    def get_json(self):
        return self.results

    def get_trend_dataframe(self):
        # TODO only for trends
        headers = []
        self.result_df = json_normalize(self.results, meta=headers)
        return self.result_df
