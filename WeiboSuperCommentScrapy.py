# -*- coding: utf-8 -*-
# pc_type           lenovo
# create_time:      2020/2/19 12:16
# file_name:        super_comment.py
# github            https://github.com/inspurer

import time
import traceback
import requests
import execjs
import http.cookiejar as cookielib
import csv
import os

comment_path = 'comment'
if not os.path.exists(comment_path):
    os.mkdir(comment_path)

agent = 'mozilla/5.0 (windowS NT 10.0; win64; x64) appLewEbkit/537.36 (KHTML, likE gecko) chrome/71.0.3578.98 safari/537.36'
my_cookie = '_T_WM=dfa6f087073666ebd21bb852a39cfcce; SCF=AhN6sTHqSyKYRLsrmPjlzzwTIAm8CZaYE2U-3CzPTVQQTiZJE63-mDQC8IXtehDn8vPiMvixyw9QSUD176dpZCY.; SUB=_2A25NGS69DeRhGeFK41EZ-SjIyzSIHXVu5bL1rDV6PUJbktANLWHSkW1NQvHi32oZjJ5U-q4DPLpdPi56eJ824MxY; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WhZoiRi.4PwaoZQAicp86k.5NHD95QNShn01h.cSh5RWs4DqcjHi--fi-2Xi-8Wxs8ai--Xi-i8i-27; SSOLoginState=1612537582'

headers = {
    'user-agent': agent,
    'Cookie': my_cookie
}

jspython = '''str62keys = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
/**
* 10进制值转换为62进制
* @param {String} int10 10进制值
* @return {String} 62进制值
*/
function int10to62(int10) {
    var s62 = '';
    var r = 0;
    while (int10 != 0) {
            r = int10 % 62;
            s62 = this.str62keys.charAt(r) + s62;
            int10 = Math.floor(int10 / 62);
    }
    return s62;
}
/**
* 62进制值转换为10进制
* @param {String} str62 62进制值
* @return {String} 10进制值
*/
function str62to10(str62) {
    var i10 = 0;
    for (var i = 0; i < str62.length; i++) {
            var n = str62.length - i - 1;
            var s = str62.substr(i, 1);  // str62[i]; 字符串用数组方式获取，IE下不支持为“undefined”
            i10 += parseInt(str62keys.indexOf(s)) * Math.pow(62, n);
    }
    return i10;
}
/**
* id转换为mid
* @param {String} id 微博id，如 "201110410216293360"
* @return {String} 微博mid，如 "wr4mOFqpbO"
*/
function id2mid(id) {
    if (typeof (id) != 'string') {
            return false; // id数值较大，必须为字符串！
    }
    var mid = '';
    for (var i = id.length - 7; i > -7; i = i - 7) //从最后往前以7字节为一组读取mid
    {
            var offset1 = i < 0 ? 0 : i;
            var offset2 = i + 7;
            var num = id.substring(offset1, offset2);
            num = int10to62(num);
            mid = num + mid;
    }
    return mid;
}
/**
* mid转换为id
* @param {String} mid 微博mid，如 "wr4mOFqpbO"
* @return {String} 微博id，如 "201110410216293360"
*/
function mid2id(mid) {
    var id = '';
    for (var i = mid.length - 4; i > -4; i = i - 4) //从最后往前以4字节为一组读取mid字符
    {
            var offset1 = i < 0 ? 0 : i;
            var len = i < 0 ? parseInt(mid.length % 4) : 4;
            var str = mid.substr(offset1, len);
            str = str62to10(str).toString();
            if (offset1 > 0) //若不是第一组，则不足7位补0
            {
                    while (str.length < 7) {
                            str = '0' + str;
                    }
            }
            id = str + id;
    }
    return id;
}'''
ctx = execjs.compile(jspython)  # 编译 js

def get_cookies():
    # 加载cookie
    cookies = cookielib.LWPCookieJar("Cookie.txt")
    cookies.load(ignore_discard=True, ignore_expires=True)
    # 将cookie转换成字典
    cookie_dict = requests.utils.dict_from_cookiejar(cookies)
    return cookie_dict


def info_parser(data):
    id, time, text = data['id'], data['created_at'], data['text']
    try:
        like_count = data['like_count']
    except:
        like_count = '数据缺失'
    user = data['user']
    uid, username, following, followed, gender = \
        user['id'], user['screen_name'], user['follow_count'], user['followers_count'], user['gender']
    return {
        'wid': id,
        'time': time,
        'text': text,
        'uid': uid,
        'like_count': like_count,
        'username': username,
        'following': following,
        'followed': followed,
        'gender': gender
    }


def start_crawl(cookie_dict, id):
    base_url = 'https://m.weibo.cn/comments/hotflow?id={}&mid={}&max_id_type=0'
    next_url = 'https://m.weibo.cn/comments/hotflow?id={}&mid={}&max_id={}&max_id_type={}'
    page = 1
    id_type = 0
    comment_count = 0
    requests_count = 1
    wids = []
    res = requests.get(url=base_url.format(id, id), headers=headers)
    while True:
        print('parse page {}'.format(page))
        page += 1
        try:
            data = res.json()['data']
            wdata = []
            max_id = data['max_id']
            for c in data['data']:
                comment_count += 1
                row = info_parser(c)
                if row['wid'] in wids:
                    print('评论抓取完成')
                    return
                wids.append(row['wid'])
                wdata.append(row)
                if c.get('comments', None):
                    temp = []
                    for cc in c.get('comments'):
                        ccc = info_parser(cc)
                        if ccc['wid'] in wids:
                            print('评论抓取完成')
                            return
                        wids.append(ccc['wid'])
                        temp.append(ccc)
                        wdata.append(ccc)
                        comment_count += 1
                    row['comments'] = temp
                print(row)
            with open('{}/{}.csv'.format(comment_path, mid), mode='a+', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                for d in wdata:
                    writer.writerow([d['wid'], d['time'], d['text'], d['uid'], d['like_count'], d['username'],
                                     d['following'], d['followed'], d['gender']])

            time.sleep(5)
        except:
            print(traceback.format_exc())
            print(res.text)
            print(res.url)
            print('评论总数: {}'.format(comment_count))
            if id_type == 1:
                break
            id_type = 1

        res = requests.get(url=next_url.format(id, id, max_id, id_type), headers=headers, cookies=cookie_dict)
        requests_count += 1
        if requests_count % 50 == 0:
            print(id_type)
        print(res.status_code)

    # TODO: Move file to another place


if __name__ == '__main__':
    global mid
    # cookie_path = "Cookie.txt"  # 保存cookie 的文件名称
    # id = '4467107636950632'     # 爬取微博的 id
    mid = 'K0DTupjf9'
    id = ctx.call('mid2id', mid)
    id = '4601532790868962'
    # WeiboLogin(username, password, cookie_path).login()
    with open('{}/{}.csv'.format(comment_path, mid), mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['wid', 'time', 'text', 'uid', 'like_count', 'username', 'following', 'followed', 'gender'])
    start_crawl(None, id)
