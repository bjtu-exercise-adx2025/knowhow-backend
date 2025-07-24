import unittest

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TestLogin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.BASE_URL = 'https://127.0.0.1:8888'

    def test_connection(self):
        """测试连接"""
        try:
            response = requests.get(self.BASE_URL, verify=False)
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.RequestException as e:
            self.fail(f"Connection failed: {e}")

    # def test_login(self):
    #     """测试登录"""
    #     data = {'username': self.username, 'password': self.password}
    #     response = requests.post(self.login_url, data=data).json()
    #     self.assertEqual(response['code'], 200)
    #     self.assertEqual(response['msg'], 'success')
    #
    # def test_info(self):
    #     """测试info接口"""
    #     data = {'username': self.username, 'password': self.password}
    #     response_cookies = requests.post(self.login_url, data=data).cookies
    #     session = response_cookies.get('session')
    #     self.assertTrue(session)
    #     info_cookies = {'session': session}
    #     response = requests.get(self.info_url, cookies=info_cookies).json()
    #     self.assertEqual(response['code'], 200)
    #     self.assertEqual(response['msg'], 'success')
    #     self.assertEqual(response['data'], 'info')


if __name__ == '__main__':
    unittest.main()
