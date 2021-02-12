# -*- coding: utf-8 -*-
# author:       Zhigong Li
# create_date:  2021/02/06

import time
import traceback
import base64
import rsa
import binascii
import requests
import re
import execjs
from PIL import Image
import random
from urllib.parse import quote_plus
import http.cookiejar as cookielib
import csv
import os

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

agent = 'mozilla/5.0 (windowS NT 10.0; win64; x64) appLewEbkit/537.36 (KHTML, likE gecko) chrome/71.0.3578.98 safari/537.36'
# Cookie needs to be set manually
my_cookie = '_T_WM=dfa6f087073666ebd21bb852a39cfcce; SCF=AhN6sTHqSyKYRLsrmPjlzzwTIAm8CZaYE2U-3CzPTVQQTiZJE63-mDQC8IXtehDn8vPiMvixyw9QSUD176dpZCY.; SUB=_2A25NGS69DeRhGeFK41EZ-SjIyzSIHXVu5bL1rDV6PUJbktANLWHSkW1NQvHi32oZjJ5U-q4DPLpdPi56eJ824MxY; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WhZoiRi.4PwaoZQAicp86k.5NHD95QNShn01h.cSh5RWs4DqcjHi--fi-2Xi-8Wxs8ai--Xi-i8i-27; SSOLoginState=1612537582'

headers = {
    'user-agent': agent,
    'Cookie': my_cookie
}

comment_path = 'comment2'
if not os.path.exists(comment_path):
    os.mkdir(comment_path)


def start_crawl(weibo_id):
    """
    @param weibo_id the id of a piece of weibo, id should be of the format like 4601532790868962
    Crawl all the comments (including comments of comments) of a piece of weibo with the id.
    """
    base_url = 'https://m.weibo.cn/comments/hotflow?id={}&mid={}&max_id_type=0'
    next_url = 'https://m.weibo.cn/comments/hotflow?id={}&mid={}&max_id={}&max_id_type={}'
    page = 1
    comment_count = 0
    max_id = 0
    max_id_type = 0
    comment_ids = []
    res = requests.get(url=base_url.format(weibo_id, weibo_id), headers=headers)

    while True:
        print('parse page {}'.format(page))
        page += 1

        try:
            data = res.json()['data']
            max_id = data['max_id']
            max_id_type = data['max_id_type']

            for comment in data['data']:
                d = info_parser(comment)
                cid = d['cid']

                if cid in comment_ids:
                    print('评论抓取完成')
                    return

                comment_ids.append(cid)
                comment_count += 1

                global writer
                print(d)
                writer.writerow([d['cid'], d['time'], d['text'], d['uid'], d['like_count'], d['username'],
                                 d['following'], d['followed'], d['gender']])

                if comment['total_number'] > 0:
                    print('Crawl children comments for {}'.format(cid))
                    crawl_nested_commends(cid)

            global f
            f.flush()

        except:
            print(traceback.format_exc())
            print(res.text)
            print(res.url)
            print('评论总数: {}'.format(comment_count))
            return

        time.sleep(4)
        res = requests.get(url=next_url.format(weibo_id, weibo_id, max_id, max_id_type), headers=headers)


def crawl_nested_commends(cid):
    """
    @param cid comment id
    @return
    """
    max_id = 0
    max_id_type = 0
    page = 1
    total_comments = 0
    base_url = 'https://m.weibo.cn/comments/hotFlowChild?cid={}&max_id={}&max_id_type={}'
    comment_ids = []
    res = requests.get(url=base_url.format(cid, max_id, max_id_type), headers=headers)

    while True:
        print('parse page {} of {}'.format(page, cid))
        page += 1

        try:
            data = res.json()['data']
            max_id = res.json()['max_id']
            max_id_type = res.json()['max_id_type']

            for comment in data:
                d = info_parser(comment)

                if d['cid'] in comment_ids:
                    print('评论抓取完成')
                    return

                comment_ids.append(d['cid'])
                total_comments += 1

                global writer
                print(d)
                writer.writerow([d['cid'], d['time'], d['text'], d['uid'], d['like_count'], d['username'],
                                 d['following'], d['followed'], d['gender']])

            global f
            f.flush()
        except:
            print(traceback.format_exc())
            print(res.text)
            print(res.url)
            print('评论总数: {}'.format(total_comments))
            break

        time.sleep(4)
        res = requests.get(url=base_url.format(cid, max_id, max_id_type), headers=headers)
        print("next request: {} {}".format(res.url, res.status_code))

    return total_comments


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
        'cid': id,
        'time': time,
        'text': text,
        'uid': uid,
        'like_count': like_count,
        'username': username,
        'following': following,
        'followed': followed,
        'gender': gender
    }


# Main

# mids = ['IujSJsi9n', 'Ivci6pi8T', 'IwowJBjCJ', 'IwLJFlK9K', 'Ixmg3v7IY', 'IxE7VfJ2L', 'IyCz8yQCp', 'IyJHxmWfs',
#         'Izc7XCDNV', 'IzV6vof2k', 'IAqT73KzS', 'IAvlUFJ18', 'IABFlayx4', 'IDhNIbI24', 'IDi6FArrm', 'J1PUeg35a',
#         'J2wo65e1d', 'J3vAkviuQ', 'J3ALlEa4T', 'J65ZQzpo8', 'J7tbhjVny', 'J89jP4Qwu', 'J8wOh3lIh', 'JcnfQA6FK',
#         'JdQMX77ci', 'Jejj12zxn', 'JeLwqfFE9', 'JfoT7iBap', 'JfBb8AuBK', 'JfPkzB4IT', 'Jh2GEnqp7', 'Jh3Fr5Tcj',
#         'Jhhhznxft', 'JiJF0njsv', 'JjEcOa8Ai', 'JmgvIkQuD', 'JmjvenEar', 'JolR0cVig']

mids = ['JB82tvv6b', 'JBbHEs6gb', 'JBqv5r1e2', 'JBr0y0VGQ', 'JBrZIATR7', 'JBBBDsXU9', 'JBDcZkR8A', 'JBXmZdRHh',
        'JC6LJ4UU9', 'JClFlhRcx', 'JClPVkH0L', 'JCvIxvmaJ', 'JCPFNgLBe', 'JCYUtDnUf', 'JCZqKq5gA', 'JCZNG2Z9v',
        'JD2AHw41D', 'JDhEouQQu', 'JDigm9YUT', 'JDkJD89hm', 'JDln88fot', 'JDHivxuXl', 'JEOftmHvu', 'JFINDlpmy',
        'JFJlPwOS5', 'IyCz8yQCp', 'IAqT73KzS', 'J1PUeg35a']

for mid in mids:
    weibo_id = ctx.call('mid2id', mid)
    f = open('{}/{}.csv'.format(comment_path, mid), mode='w', encoding='utf-8-sig', newline='')
    writer = csv.writer(f)
    writer.writerow(['wid', 'time', 'text', 'uid', 'like_count', 'username', 'following', 'followed', 'gender'])
    f.flush()

    start_crawl(weibo_id)
    f.close()
