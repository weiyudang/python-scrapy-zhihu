#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Build-in / Std
import os, sys, time, platform, random
import re, json, cookielib
from getpass import getpass

import requests, termcolor
reload(sys)   
sys.setdefaultencoding('utf-8')

# requirements
import requests, termcolor


requests = requests.Session()
requests.cookies = cookielib.LWPCookieJar('cookies')
try:
    requests.cookies.load(ignore_discard=True)
except:
    pass

class Logging:
    flag = True

    @staticmethod
    def error(msg):
        if Logging.flag == True:
            print "".join(  [ termcolor.colored("ERROR", "red"), ": ", termcolor.colored(msg, "white") ] )
    @staticmethod
    def warn(msg):
        if Logging.flag == True:
            print "".join(  [ termcolor.colored("WARN", "yellow"), ": ", termcolor.colored(msg, "white") ] )
    @staticmethod
    def info(msg):
        # attrs=['reverse', 'blink']
        if Logging.flag == True:
            print "".join(  [ termcolor.colored("INFO", "magenta"), ": ", termcolor.colored(msg, "white") ] )
    @staticmethod
    def debug(msg):
        if Logging.flag == True:
            print "".join(  [ termcolor.colored("DEBUG", "magenta"), ": ", termcolor.colored(msg, "white") ] )
    @staticmethod
    def success(msg):
        if Logging.flag == True:
            print "".join(  [ termcolor.colored("SUCCES", "green"), ": ", termcolor.colored(msg, "white") ] )

# Setting Logging
Logging.flag = True

class LoginPasswordError(Exception):
    def __init__(self, message):
        if type(message) != type("") or message == "": self.message = u"帐号密码错误"
        else: self.message = message
        Logging.error(self.message)

class NetworkError(Exception):
    def __init__(self, message):
        if type(message) != type("") or message == "": self.message = u"网络异常"
        else: self.message = message
        Logging.error(self.message)
class AccountError(Exception):
    def __init__(self, message):
        if type(message) != type("") or message == "": self.message = u"帐号类型错误"
        else: self.message = message
        Logging.error(self.message)





def download_captcha():
     headers = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36",
    }
    url = "https://www.zhihu.com/captcha.gif"
    r = requests.get(url, params={"r": random.random(), "type": "login"}, headers= headers,verify=False)
    if int(r.status_code) != 200:
        raise NetworkError(u"验证码请求失败")
    image_name = u"verify." + r.headers['content-type'].split("/")[1]
    open( image_name, "wb").write(r.content)
    """
        System platform: https://docs.python.org/2/library/platform.html
    """
    Logging.info(u"正在调用外部程序渲染验证码 ... ")
    if platform.system() == "Linux":
        Logging.info(u"Command: xdg-open %s &" % image_name )
        os.system("xdg-open %s &" % image_name )
    elif platform.system() == "Darwin":
        Logging.info(u"Command: open %s &" % image_name )
        os.system("open %s &" % image_name )
    elif platform.system() in ("SunOS", "FreeBSD", "Unix", "OpenBSD", "NetBSD"):
        os.system("open %s &" % image_name )
    elif platform.system() == "Windows":
        os.system("%s" % image_name )
    else:
        Logging.info(u"我们无法探测你的作业系统，请自行打开验证码 %s 文件，并输入验证码。" % os.path.join(os.getcwd(), image_name) )

    sys.stdout.write(termcolor.colored(u"请输入验证码: ", "cyan") )
    captcha_code = raw_input( )
    return captcha_code



def build_form(account, password):
    if re.match(r"^1\d{10}$", account): account_type = "phone_num"
    elif re.match(r"^\S+\@\S+\.\S+$", account): account_type = "email"
    else: raise AccountError(u"帐号类型错误")

    form = {account_type: account, "password": password, "remember_me": True }

    #form['_xsrf'] = search_xsrf()
    form['captcha'] = download_captcha()
    return form

def upload_form(form):
    if "email" in form:
        url = "https://www.zhihu.com/login/email"
    elif "phone_num" in form:
        url = "https://www.zhihu.com/login/phone_num"
    else:
        raise ValueError(u"账号类型错误")

    headers = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36",
        'Host': "www.zhihu.com",
        'Origin': "http://www.zhihu.com",
        'Pragma': "no-cache",
        'Referer': "http://www.zhihu.com/",
        'X-Requested-With': "XMLHttpRequest"
    }

    r = requests.post(url, data=form, headers=headers, verify=False)
    if int(r.status_code) != 200:
        raise NetworkError(u"表单上传失败!")

    if r.headers['content-type'].lower() == "application/json":
        try:
            # 修正  justkg 提出的问题: https://github.com/egrcc/zhihu-python/issues/30
            result = json.loads(r.content)
        except Exception as e:
            Logging.error(u"JSON解析失败！")
            Logging.debug(e)
            Logging.debug(r.content)
            result = {}
        if result["r"] == 0:
            Logging.success(u"登录成功！" )
            return {"result": True}
        elif result["r"] == 1:
            Logging.success(u"登录失败！" )
            return {"error": {"code": int(result['errcode']), "message": result['msg'], "data": result['data'] } }
        else:
            Logging.warn(u"表单上传出现未知错误: \n \t %s )" % ( str(result) ) )
            return {"error": {"code": -1, "message": u"unknown error"} }
    else:
        Logging.warn(u"无法解析服务器的响应内容: \n \t %s " % r.text )
        return {"error": {"code": -2, "message": u"parse error"} }


def islogin():
    # check session
    url = "https://www.zhihu.com/settings/profile"
    r = requests.get(url,allow_redirects=False)
    status_code = int(r.status_code)
    if status_code == 301 or status_code == 302:
        # 未登录
        return False
    elif status_code == 200:
        return True
    else:
        Logging.warn(u"网络故障")
        return None




def login(account=None, password=None):
    if islogin() == True:
        Logging.success(u"你已经登录过咯")
        return True


    if account == None:
        sys.stdout.write(u"请输入登录账号: ")
        account  = raw_input()
        password = getpass("请输入登录密码: ")

    form_data = build_form(account, password)
    """
        result:
            {"result": True}
            {"error": {"code": 19855555, "message": "unknown.", "data": "data" } }
            {"error": {"code": -1, "message": u"unknown error"} }
    """
    result = upload_form(form_data)
    if "error" in result:
        if result["error"]['code'] == 1991829:
            # 验证码错误
            Logging.error(u"验证码输入错误，请准备重新输入。" )
            return login()
        elif result["error"]['code'] == 100005:
            # 密码错误
            Logging.error(u"密码输入错误，请准备重新输入。" )
            return login()
        else:
            Logging.warn(u"unknown error." )
            return False
    elif "result" in result and result['result'] == True:
        # 登录成功
        Logging.success(u"登录成功！" )
        requests.cookies.save()
        return True

if __name__ == "__main__":
    # login(account="xxxx@email.com", password="xxxxx")
    login()
