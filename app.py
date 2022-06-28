import sys
import os
import requests
from datetime import datetime
from urllib.parse import quote


class DouyinOpenQuotaReport(object):
    """抖音开放平台配额提醒"""

    def __init__(
        self,
        dingtalk_bot_keyword,
        dingtalk_bot_token,
        douyin_client_key,
        douyin_cookies,
    ):
        self.DINGTALK_BOT_KEYWORD = dingtalk_bot_keyword
        self.DINGTALK_BOT_TOKEN = dingtalk_bot_token
        self.DOUYIN_CLIENT_KEY = douyin_client_key
        self.DOUYIN_COOKIES = douyin_cookies

    def get_url(self, type=None):
        domain = "https://open.douyin.com/aweme/v2/platform/app/quota"
        if type == "platform":
            return "https://open.douyin.com/platform/management/app/data/{}".format(
                self.DOUYIN_CLIENT_KEY
            )
        elif type == "package":
            return "{}/package/list/?client_key={}&page=1&page_size=5&_t={}".format(
                domain, self.DOUYIN_CLIENT_KEY, int(datetime.now().timestamp())
            )
        elif type == "service":
            return "{}/service/list/?client_key={}&_t={}".format(
                domain, self.DOUYIN_CLIENT_KEY, int(datetime.now().timestamp())
            )
        else:
            return None

    def get_dingtalk_webhook(self):
        return "https://oapi.dingtalk.com/robot/send?access_token={}".format(
            self.DINGTALK_BOT_TOKEN
        )

    def get_dingtalk_link(self, url):
        return "dingtalk://dingtalkclient/page/link?url={}&pc_slide=false".format(
            quote(url)
        )

    def get_headers(self):
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,en-HK;q=0.7,ja-JP;q=0.6,ja;q=0.5,en-US;q=0.4,zh-TW;q=0.3",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "cookie": self.DOUYIN_COOKIES,
            "Referer": "https://open.douyin.com/platform/management/app/data/{}".format(
                self.DOUYIN_CLIENT_KEY
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

    def quota_package_list(self):
        try:
            r = requests.get(self.get_url("package"), headers=self.get_headers())
            quota_package_list = r.json()["data"]["quota_package_list"]
            quota_package_list = [
                package for package in quota_package_list if package["remain_count"] > 0
            ]
            return quota_package_list
        except:
            print("⚠️ 接口响应格式错误, 返回值: {}".format(r.text))
            return None

    def quota_service(self):
        r = requests.get(self.get_url("service"), headers=self.get_headers())
        try:
            quota_service = r.json()["data"]["quota_service_list"][0]
            usage_by_days = [
                {"time": datetime.fromtimestamp(int(key)), "count": value["count"]}
                for key, value in quota_service["usage_by_days"].items()
            ]
            usage_by_days.sort(key=lambda x: x["time"])
            quota_service["usage_by_days"] = usage_by_days
            usage_by_hours = [
                {"time": datetime.fromtimestamp(int(key)), "count": value["count"]}
                for key, value in quota_service["usage_by_hours"].items()
            ]
            usage_by_hours.sort(key=lambda x: x["time"])
            quota_service["usage_by_hours"] = usage_by_hours
            return quota_service
        except:
            print("⚠️ 接口响应格式错误, 返回值: {}".format(r.text))
            return None

    def generate_message(self, package_list, service):
        text = "# 抖音开放平台配额套餐\n\n"

        if package_list and len(package_list) > 0:
            for package in package_list:
                text += "## 💰 {} 状态: {}\n".format(
                    package["package_name"],
                    "生效中" if package["package_status"] == 1 else "消耗完成",
                )
                text += "- 剩余服务次数/总次数: {}/{}\n".format(
                    package["remain_count"], package["total_count"]
                )
                text += "- 套餐失效时间: {}\n".format(
                    datetime.fromtimestamp(package["end_time_by_sec"])
                )
                text += "- 剩余有效期/有效期: {}/{}\n".format(
                    package["remain_time_by_day"], package["total_time_by_day"]
                )
        else:
            text += "## 💰 暂无套餐\n请确认是否已失效\n"

        text += "\n"

        if service:
            text += "## 📊 {} 调用量数据: \n".format(service["service_name"])
            usage_by_days = service["usage_by_days"]
            usage_by_days = usage_by_days[-3 : len(usage_by_days)]
            for usage in usage_by_days:
                text += "- {}: {}\n".format(
                    usage["time"].strftime("%Y-%m-%d"), usage["count"]
                )
        else:
            text += "## 📊 暂无调用量数据\n请确认授权是否已失效\n"

        text += "\n"

        message = {
            "msgtype": "actionCard",
            "actionCard": {
                "title": "[{}]Douyin Open Platform API Quota".format(
                    self.DINGTALK_BOT_KEYWORD
                ),
                "text": text,
                "btnOrientation": "0",
                "singleTitle": "前往抖音开放平台查看",
                "singleURL": self.get_dingtalk_link(self.get_url("platform")),
            },
        }
        return message

    def send_message(self, message):
        result = requests.post(self.get_dingtalk_webhook(), json=message)
        if result.status_code == 200 and result.json()["errcode"] == 0:
            print("✔️ 通知发送成功")
            sys.exit(0)
        else:
            print("❌ 通知发送失败: {}".format(result.text))
            sys.exit("Webhook failed to send: {}".format(result.text))

    def run(self):
        package_list = self.quota_package_list()
        service = self.quota_service()
        message = self.generate_message(package_list, service)
        print(message)
        self.send_message(message)


if __name__ == "__main__":
    if not os.environ.get("DINGTALK_BOT_KEYWORD"):
        print("❌ 未设置钉钉机器人关键字")
        sys.exit("Please set DINGTALK_BOT_KEYWORD")

    if not os.environ.get("DINGTALK_BOT_TOKEN"):
        print("❌ 未设置钉钉机器人 Token")
        sys.exit("Please set DINGTALK_BOT_TOKEN")

    if not os.environ.get("DOUYIN_CLIENT_KEY"):
        print("❌ 未设置抖音 Client Key")
        sys.exit("Please set DOUYIN_CLIENT_KEY")

    if not os.environ.get("DOUYIN_COOKIES"):
        print("❌ 未设置抖音 Cookies")
        sys.exit("Please set DOUYIN_COOKIES")

    DouyinOpenQuotaReport(
        os.environ["DINGTALK_BOT_KEYWORD"],
        os.environ["DINGTALK_BOT_TOKEN"],
        os.environ["DOUYIN_CLIENT_KEY"],
        os.environ["DOUYIN_COOKIES"],
    ).run()
