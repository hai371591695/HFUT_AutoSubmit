import requests
import json
import time
import datetime
import pytz
import base64
import argparse
from Crypto.Cipher import AES
from requests.sessions import session
import os

output_data = ""

class hfuter:
    def __init__(self, username, password) -> None:
        global output_data
        super().__init__()

        self.session = requests.session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/83.0.4103.61 Safari/537.36 Edg/83.0.478.37",
            "Accept": "application/json, text/plain, */*",
        })

        self.username = username
        self.password = password

        ret = self.__login()
        if ret:
            output_data += "{username}登录成功%0D%0A%0D%0A".format(username=self.username)
            self.logged_in = True
        else:
            output_data +=  "{username}登录失败！%0D%0A%0D%0A".format(username=self.username)
            self.logged_in = False

    def __login(self) -> bool:
        global output_data
        def encrypt_password(text: str, key: str):
            """encrypt password"""
            def pad(data_to_pad, block_size, style='pkcs7'):
                """Apply standard padding.

                Args:
                data_to_pad (byte string):
                    The data that needs to be padded.
                block_size (integer):
                    The block boundary to use for padding. The output length is guaranteed
                    to be a multiple of :data:`block_size`.
                style (string):
                    Padding algorithm. It can be *'pkcs7'* (default), *'iso7816'* or *'x923'*.

                Return:
                byte string : the original data with the appropriate padding added at the end.
                """
                def bchr(s):
                    return bytes([s])

                padding_len = block_size-len(data_to_pad) % block_size
                if style == 'pkcs7':
                    padding = bchr(padding_len)*padding_len
                elif style == 'x923':
                    padding = bchr(0)*(padding_len-1) + bchr(padding_len)
                elif style == 'iso7816':
                    padding = bchr(128) + bchr(0)*(padding_len-1)
                else:
                    raise ValueError("Unknown padding style")
                return data_to_pad + padding
            key = key.encode('utf-8')
            text = text.encode('utf-8')

            text = pad(text, len(key), style='pkcs7')

            aes = AES.new(key, AES.MODE_ECB)
            password = aes.encrypt(text)
            password = base64.b64encode(password)
            return password

        ret = self.session.get("https://cas.hfut.edu.cn/cas/login")
        # JSESSIONID
        ret = self.session.get('https://cas.hfut.edu.cn/cas/vercode')
        # check if needs Vercode
        millis = int(round(time.time() * 1000))
        ret = self.session.get(
            'https://cas.hfut.edu.cn/cas/checkInitVercode', params={'_': millis})
        key = ret.cookies['LOGIN_FLAVORING']

        if ret.json():
            # needs OCR! will be done later.
            output_data += '需验证码，目前该功能此脚本未支持%0D%0A%0D%0A'
            return False
        else:
            output_data += '无需验证码%0D%0A%0D%0A'

        # 加密密码
        password = encrypt_password(self.password, key)

        # 先get
        ret = self.session.get(
            'https://cas.hfut.edu.cn/cas/policy/checkUserIdenty',
            params={'_': millis+1, 'username': self.username, 'password': password})

        ret = ret.json()

        # 判断是否成功
        if ret['msg'] != 'success' and not ret['data']['authFlag']:
            return False

        if ret['data']['mailRequired'] or ret['data']['phoneRequired']:
            output_data += "你需要先进行手机或者邮箱的认证，请在PC上打开cas.hfut.edu.cn页面进行登录之后才可使用此脚本%0D%0A%0D%0A"
            return False

        # 然后post
        self.session.headers.update(
            {"Content-Type": "application/x-www-form-urlencoded"})
        ret = self.session.post(
            'https://cas.hfut.edu.cn/cas/login',
            data={
                'username': self.username,
                'capcha': "",
                'execution': "e1s1",
                '_eventId': "submit",
                'password': password,
                'geolocation': "",
                'submit': "登录"
            })
        self.session.headers.pop("Content-Type")

        if ret.text.find("cas协议登录成功跳转页面") != -1:
            return True
        else:
            return False

    def basic_infomation(self):
        global output_data
        if not self.logged_in:
            return {}

        self.session.get(
            "http://stu.hfut.edu.cn/xsfw/sys/swmjbxxapp/*default/index.do")

        self.session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest"
        })
        self.session.post(
            "http://stu.hfut.edu.cn/xsfw/sys/emapfunauth/welcomeAutoIndex.do"
        )
        self.session.headers.pop("Content-Type")
        self.session.headers.pop("X-Requested-With")

        ret = self.session.get(
            "http://stu.hfut.edu.cn/xsfw/sys/emapfunauth/casValidate.do",
            params={
                'service': '/xsfw/sys/swmjbxxapp/*default/index.do'
            }
        )

        self.session.headers.update({"X-Requested-With": "XMLHttpRequest"})
        self.session.headers.update(
            {"Referer": "http://stu.hfut.edu.cn/xsfw/sys/swmjbxxapp/*default/index.do"})
        ret = self.session.get(
            "http://stu.hfut.edu.cn/xsfw/sys/emappagelog/config/swmjbxxapp.do")
        self.session.headers.pop("X-Requested-With")

        config_data = {"APPID": "4930169432823497", "APPNAME": "swmjbxxapp"}
        self.session.headers.update(
            {"Content-Type": "application/x-www-form-urlencoded"})
        ret = self.session.post(
            "http://stu.hfut.edu.cn/xsfw/sys/swpubapp/MobileCommon/getSelRoleConfig.do",
            data={"data": json.dumps(config_data)}
        ).json()
        if ret["code"] != "0":
            output_data += ret["msg"] + '%0D%0A%0D%0A'
            return {}
        ret = self.session.post(
            "http://stu.hfut.edu.cn/xsfw/sys/swpubapp/MobileCommon/getMenuInfo.do",
            data={"data": json.dumps(config_data)}
        ).json()
        if ret["code"] != "0":
            output_data += ret["msg"] + '%0D%0A%0D%0A'
            return {}
        self.session.headers.pop("Content-Type")

        info = self.session.get(
            "http://stu.hfut.edu.cn/xsfw/sys/swmjbxxapp/StudentBasicInfo/initPageConfig.do", params={"data": "{}"}).json()
        self.session.headers.pop("Referer")

        return info['data']

    def daily_checkin(self, address: str) -> bool:
        global output_data
        if not self.logged_in:
            return False

        today = datetime.datetime.now(
            tz=pytz.timezone('Asia/Shanghai')).timetuple()[:3]
        self.session.get(
            "http://stu.hfut.edu.cn/xsfw/sys/swmxsyqxxsjapp/*default/index.do")

        self.session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest"
        })
        self.session.post(
            "http://stu.hfut.edu.cn/xsfw/sys/emapfunauth/welcomeAutoIndex.do"
        )
        self.session.headers.pop("Content-Type")
        self.session.headers.pop("X-Requested-With")

        ret = self.session.get(
            "http://stu.hfut.edu.cn/xsfw/sys/emapfunauth/casValidate.do",
            params={
                'service': '/xsfw/sys/swmjbxxapp/*default/index.do'
            }
        )

        self.session.headers.update({"X-Requested-With": "XMLHttpRequest"})
        self.session.headers.update(
            {"Referer": "http://stu.hfut.edu.cn/xsfw/sys/swmjbxxapp/*default/index.do"})
        ret = self.session.get(
            "http://stu.hfut.edu.cn/xsfw/sys/emappagelog/config/swmxsyqxxsjapp.do")
        self.session.headers.pop("X-Requested-With")

        config_data = {"APPID": "5811260348942403",
                       "APPNAME": "swmxsyqxxsjapp"}
        self.session.headers.update(
            {"Content-Type": "application/x-www-form-urlencoded"})
        ret = self.session.post(
            "http://stu.hfut.edu.cn/xsfw/sys/swpubapp/MobileCommon/getSelRoleConfig.do",
            data={"data": json.dumps(config_data)}
        ).json()
        if ret["code"] != "0":
            output_data += ret["msg"]  + '%0D%0A%0D%0A'
            return False
        ret = self.session.post(
            "http://stu.hfut.edu.cn/xsfw/sys/swpubapp/MobileCommon/getMenuInfo.do",
            data={"data": json.dumps(config_data)}
        ).json()
        if ret["code"] != "0":
            output_data += ret["msg"] + '%0D%0A%0D%0A'
            return False
        self.session.headers.pop("Content-Type")

        info = self.session.get(
            "http://stu.hfut.edu.cn/xsfw/sys/swmxsyqxxsjapp/modules/mrbpa/getSetting.do",
            data={"data": "{}"}
        ).json()

        start_time = "%04d-%02d-%02d " % today + \
            info['data']['DZ_TBKSSJ'] + " +0800"
        start_time = datetime.datetime.strptime(
            start_time, "%Y-%m-%d %H:%M:%S %z")
        end_time = "%04d-%02d-%02d " % today + \
            info['data']['DZ_TBJSSJ'] + " +0800"
        end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S %z")
        now_time = datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))

        output_data += "打卡起始时间:" + str(start_time) + '%0D%0A%0D%0A'
        output_data += "打卡结束时间:" + str(end_time) + '%0D%0A%0D%0A'
        output_data += "　　现在时间:"+ str(now_time) + '%0D%0A%0D%0A'
        if start_time < now_time and now_time < end_time:
            output_data += "在打卡时间内" + '%0D%0A%0D%0A'
        else:
            output_data += "不在打卡时间内" + '%0D%0A%0D%0A'
            return False

        self.session.headers.update(
            {"Content-Type": "application/x-www-form-urlencoded"})
        last_form = self.session.post(
            "http://stu.hfut.edu.cn/xsfw/sys/swmxsyqxxsjapp/modules/mrbpa/getStuXx.do",
            data={"data": json.dumps({"TBSJ": "%.2d-%.2d-%.2d" % today})}
        ).json()
        if last_form['code'] != "0":
            return False

        new_form = last_form['data']
        new_form.update({
            "DZ_SFSB": "1",
            "GCKSRQ": "",
            "GCJSRQ": "",
            "DFHTJHBSJ": "",
            "DZ_TBDZ": address,
            "BY1": "1",
            "TBSJ": "%.2d-%.2d-%.2d" % today
        })

        ret = self.session.post(
            "http://stu.hfut.edu.cn/xsfw/sys/swmxsyqxxsjapp/modules/mrbpa/saveStuXx.do",
            data={"data": json.dumps(new_form)}
        ).json()

        self.session.headers.pop("Content-Type")
        self.session.headers.pop("Referer")
        return ret['code'] == "0"


# An example code demonstrating how to use the interfaces.
# actually, it was already usable.

def main():
    global output_data
    env_dist = os.environ

    stu = hfuter(username=env_dist['username'], password=env_dist['password'])
    if stu.daily_checkin(env_dist['address']):
        requests.post('https://sc.ftqq.com/'+env_dist['sckey']+'.send?title=自动打卡成功&desp='+output_data)
    else:
        requests.post('https://sc.ftqq.com/'+env_dist['sckey']+'.send?title=自动打卡失败&desp='+output_data)

if __name__ == "__main__":
    main()
