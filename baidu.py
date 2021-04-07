# -*- coding: UTF-8 -*-
import requests
from bs4 import BeautifulSoup
import re
import csv
from datetime import datetime
import queue
import threading
import os, sys, pretty_errors

baseUrl = 'http://www.baidu.com/s'
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br'
}

def parse_default(element):
    return { 'title': element.select('h3')[0].get_text(), 'url': element.select('h3 a')[0].attrs['href'] }

def parse_img(element):
    res = list(map(lambda e: {'title': e.get_text(), 'url': e.attrs['href']}, element.select("span.op-img-address-link-menu a")))
    return { 'url': element.attrs['mu'], 'tags': res }
    pass

def parse_tieba(element):
    return { 'title': element.select('h3 a')[0].get_text().strip() }

def parse_bk(element):
    print('parse_bk', element.select('h3')[0].get_text().strip(), element.attrs['mu'])
    pass

def parse_recommend_list(element):
    return list(map(lambda e: e.get_text(), element("a")))

def parse_realtime(element):
    print('parse_realtime', element.attrs['mu'])
    return

def parse_video(element):
    # https://www.baidu.com/sf/vsearch?pd=video&wd=%E7%90%86%E8%B4%A2
    print('parse_video',  )
    for e in element.select('div.op-short-video-pc div.c-span3 a:first'):
        print(e.attrs['title'], e.attrs['href'])
        print(e)
    return 

def parse_hd_video(element):
    res = element.select('div.c-result-content header a')
    print('parse_hd_video',)
    for e in res:
        print(e.get_text(), e['href'])
    #res = [( e.attrs) for e in res]
    return

def parse_st_com_abstract(element):
    a = element.select('div a:has(span:contains("下载地址"))')[0]
    footer = element.select('div a.c-showurl')[0]

    return { 'title': footer.get_text(), 'url': a['href'] }

tpl_list = {
    'se_com_default': parse_default, # 搜索结果
    'img_address': parse_img, # 图片搜索
    'tieba_general': parse_tieba, # 贴吧
    'bk_polysemy': parse_bk, # 百科
    'recommend_list': parse_recommend_list, # 其他人还在搜
    'sp_realtime_bigpic5': parse_realtime, # xxx的最新相关信息 - 资讯搜索
    'short_video_pc': parse_video, # 视频搜索
    'yl_vd_kg_pc': parse_hd_video, # 高清视频在线观看
    'se_st_com_abstract': parse_st_com_abstract, # 下载
}

def search(keyword):
    print("*"*5, "检索", keyword, "*"*5)
    data = {'wd': keyword}
    r = requests.get(url=baseUrl, params=data, headers=headers)
    if r.status_code == 200:
        bso = BeautifulSoup(r.text, 'html.parser')
        content = bso.select('div.head_nums_cont_outer span.nums_text')[0]
        number = re.findall('百度为您找到相关结果约(.*?)个', content.getText(), re.I)[0]

        result = { 'total': number, 'advertisement': [] }

        content = bso.select('#content_left > div.c-container')
        for item in content:
            if 'tpl' in item.attrs:
                tpl = item.attrs['tpl']
                if tpl not in result:
                    result[tpl] = []
                if tpl in tpl_list:
                    result[tpl].append(tpl_list[tpl](item))
                else:
                    print("Missing TPL", tpl)
                    print(item)
            elif 'cmatchid' in item.attrs:
                a = item.select('a[data-is-main-url]')[0]
                result['advertisement'].append({
                    'title': a.getText(),
                    'url': a.attrs['data-landurl']
                })
            else:
                print(item)

        # 相关搜索
        res = list(map(lambda e: e.get_text(), bso.select("#rs table th ")))
        result['related_search'] = res
        return result
    else:
        print("Fail Code", r.status_code)
        return None

class BaiduKeyword(object):
    def __init__(self, thread=20):
        self.csv_header = ['keyword', 'number', 'time']
        self.keyword_queue = queue.Queue()
        self.thread = thread

    def Spider(self):
        while not self.keyword_queue.empty():
            keyword = self.keyword_queue.get()
            res = search(keyword)
            if len(res['advertisement']):
                print("广告")
                for e in res['advertisement']:
                    print(e['title'], e['url'])
            if 'recommend_list' in res:
                print("\n其他人还在搜")
                print('\n'.join(res['recommend_list'][0]))
            print("\n相关搜索")
            print('\n'.join(res['related_search']))
            #print(res)

    def run(self, path=None):
        with open(path) as kwf:
            for k in kwf.readlines():
                self.keyword_queue.put(k.strip())

        thread_list = []
        for i in range(min(self.thread, self.keyword_queue.qsize())):
            t = threading.Thread(target=self.Spider)
            thread_list.append(t)
            for t in thread_list:
                t.setDaemon(True)
                t.start()
            for t in thread_list:
                t.join()

if __name__ == '__main__':
    #print('*' * 30)
    #try:
    #    thread = int(input("请设置线程数（默认1）：") or 1)
    #except:
    #    print("请输入大于0的整数！！！")
    #    sys.exit(0)
    #if not isinstance(thread, int):
    #    print("参数设置错误，请输入整数！")
    #    sys.exit(0)
    #filename = input("输入存放关键词的文件（默认keywords.txt）：") or 'keywords.txt'

    #if not os.path.exists('./result'):
    #    os.mkdir('./result')
    thread = 1
    filename = 'keywords.txt'

    if not os.path.exists(filename):
        print(f'文件{filename}不存在，退出')
    else:
        print('*' * 10 + '开始爬取' + '*' * 10)

        BaiduKeyword(thread=thread).run(filename)

# https://www.baidu.com/search/rss.html
