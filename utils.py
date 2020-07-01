import requests
from bs4 import BeautifulSoup as BS
from os import makedirs, remove
from os.path import exists, join
import datetime


url = "https://danbooru.donmai.us/posts?page=1"
fpath = "C:\\TMP\\booru\\"
container_d = []


def get_name(url):
    return url.split("/")[-1]


def get_page(url, flag="p", params=None):
    _HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0',
                'accept': '*/*'}
    try:
        if flag =="b":
            req1 = requests.get(url, stream=True, params=params, headers=_HEADERS)
        else:
            req1 = requests.get(url, params=params, headers=_HEADERS)
    except Exception as err:
        print(err)
        exit(1)
    if flag == "b":
        return req1.raw
    else:
        return req1.content


def get_pages(url, params=None):
    req = get_page(url, params=params)
    html = BS(req, "html.parser")
    e0 = html.select(".post-preview")
    e0 = html.find_all('article', class_='post-preview')
    for e in e0:
        img_url = e.attrs["data-large-file-url"]
        container_d.append(e.attrs)
    return container_d


def get_mini(url):
    req = get_page(url)
    html = BS(req, "html.parser")
    e0 = html.select(".has-cropped-true")
    for e in e0:
        img_url = e.attrs["src"]
        container_d.append(img_url)


def save(data, url):
    fpath = "D:\\TMP\\booru\\"
    date = datetime.date.today().isoformat()
    fpath = join(fpath, date)
    fname = url.split("/")[-1]
    if not exists(fpath):
        makedirs(fpath)
    fname = join(fpath, fname)
    if not exists(fname):
        with open(fname, "wb") as f:
            f.write(data)
