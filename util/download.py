import os
import re

import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random
from getpass import getpass
import json


class ZLibrary:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://zh.zlibrarye.ru"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',

        }
        self.logged_in = False

    def login(self, email=None, password=None):
        """登录Z-Library"""
        try:
            login_url = f"{self.base_url}/rpc.php"

            login_data = {
                'isModal': 'true',
                'email': email if email else "657266149@qq.com",
                'password': password if password else "1626459223.lgh",
                'site_mode': 'books',
                'action': 'login',
                'redirectUrl': '',
                'gg_json_mode': '1'
            }

            # 提交登录请求
            response = self.session.post(
                login_url,
                data=login_data,
                headers=self.headers,
            )
            response.raise_for_status()

            # 解析响应
            try:
                response_content = response.json()
                response_data = response_content['response']

                # 检查是否登录成功
                if 'user_id' in response_data and 'user_key' in response_data:
                    # 设置必要的cookies
                    self.session.cookies.update({
                        'remix_userid': str(response_data['user_id']),
                        'remix_userkey': response_data['user_key'],
                        'siteLanguage': 'zh',
                        'selectedSiteMode': 'books'
                    })

                    # 如果有重定向URL，执行重定向
                    if 'priorityRedirectUrl' in response_data:
                        redirect_url = response_data['priorityRedirectUrl']
                        if not redirect_url.startswith('http'):
                            redirect_url = f"{self.base_url}{redirect_url}"
                        redirect_response = self.session.get(redirect_url, headers=self.headers)
                        redirect_response.raise_for_status()

                    self.logged_in = True
                    print("登录成功!")
                    return True
                else:
                    print("登录失败，响应中缺少用户信息")
                    return False

            except json.JSONDecodeError:
                print("登录响应不是有效的JSON格式")
                return False

        except Exception as e:
            print(f"登录时出错: {e}")
            return False

    # 其余方法保持不变...
    def search_books(self, book_name):
        """搜索书籍"""
        try:
            search_url = f"{self.base_url}/s/?q={urllib.parse.quote(book_name)}"
            # 添加随机延迟以避免被检测为机器人
            time.sleep(random.uniform(1, 3))
            response = self.session.get(search_url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            book_items = soup.select('.book-item.resItemBoxBooks')
            print(f"找到 {len(book_items)} 个书籍条目")  # 调试
            # 解析搜索结果 - 根据新的HTML结构调整
            for item in book_items:
                # 提取标题
                title_elem = item.select_one('z-bookcard div[slot="title"]')
                title = title_elem.get_text(strip=True) if title_elem else "未知标题"

                # 提取作者
                author_elem = item.select_one('z-bookcard div[slot="author"]')
                authors = author_elem.get_text(strip=True) if author_elem else "未知作者"

                # 提取下载链接
                download_elem = item.select_one('z-bookcard')
                download_link = download_elem[
                    'download'] if download_elem and 'download' in download_elem.attrs else None
                # 提取文件信息
                extension_elem = item.select_one('z-bookcard')
                extension = extension_elem[
                    'extension'] if extension_elem and 'extension' in extension_elem.attrs else "未知格式"

                filesize_elem = item.select_one('z-bookcard')
                filesize = filesize_elem['filesize'] if filesize_elem and 'filesize' in filesize_elem.attrs else "未知大小"

                if download_link:
                    results.append({
                        'title': title,
                        'authors': authors,
                        'download_link': f"{self.base_url}{download_link}" if not download_link.startswith(
                            'http') else download_link,
                        'extension': extension,
                        'filesize': filesize
                    })

            return results

        except Exception as e:
            print(f"搜索书籍时出错: {e}")
            return None

    def download_book(self, download_url, save_path):
        """下载书籍文件"""
        try:
            # 添加随机延迟
            time.sleep(random.uniform(1, 3))

            # 允许重定向，并设置stream=True以流式下载
            response = self.session.get(download_url, headers=self.headers, stream=True, allow_redirects=True)
            response.raise_for_status()

            # 检查是否是真实的文件
            if 'content-disposition' not in response.headers:
                print("下载链接无效，可能需要登录或达到下载限制")
                return None

            # 从Content-Disposition获取文件名
            content_disposition = response.headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                # 处理可能的两种格式：filename="..."和filename*=UTF-8''...
                if 'filename*=' in content_disposition:
                    # 优先使用filename*，因为它支持UTF-8编码
                    filename_part = content_disposition.split('filename*=')[1]
                    filename = filename_part.split("'")[-1]  # 获取UTF-8''后面的部分
                    filename = urllib.parse.unquote(filename)
                else:
                    filename = content_disposition.split('filename=')[1].strip('"')
            else:
                # 如果没有Content-Disposition，从URL中提取文件名
                filename = os.path.basename(urllib.parse.urlparse(download_url).path)
                # 如果没有扩展名，尝试从Content-Type推断
                content_type = response.headers.get('content-type', '')
                if '.' not in filename and content_type:
                    ext = content_type.split('/')[-1].lower()
                    if len(ext) <= 5:  # 假设扩展名不超过5个字符
                        filename = f"{filename}.{ext}"

            # 确保文件名是有效的
            filename = re.sub(r'[\\/*?:"<>|]', '_', filename)  # 替换非法字符
            full_path = os.path.join(save_path, filename)

            # 确保文件名唯一
            counter = 1
            while os.path.exists(full_path):
                name, ext = os.path.splitext(filename)
                full_path = os.path.join(save_path, f"{name}_{counter}{ext}")
                counter += 1

            # 获取文件大小用于进度显示
            file_size = int(response.headers.get('content-length', 0))

            print(f"正在下载: {filename} ({file_size / 1024 / 1024:.2f} MB)")

            # 使用进度条下载
            with open(full_path, 'wb') as f:
                downloaded = 0
                start_time = time.time()
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # 显示下载进度
                        if file_size > 0:
                            percent = downloaded * 100 / file_size
                            speed = downloaded / (time.time() - start_time) / 1024  # KB/s
                            print(
                                f"\r进度: {percent:.1f}% | {downloaded / 1024 / 1024:.2f}/{file_size / 1024 / 1024:.2f} MB | 速度: {speed:.2f} KB/s",
                                end='')

            print(f"\n下载完成! 文件保存在: {full_path}")
            return full_path

        except Exception as e:
            print(f"下载书籍时出错: {e}")
            return None


def main():
    print("Z-Library 书籍下载工具")
    print("=" * 30)

    # 初始化ZLibrary客户端
    zlib = ZLibrary()

    # 尝试登录
    if not zlib.login():
        print("登录失败，无法继续")
        return

    book_name = input("请输入要搜索的书籍名称: ").strip()
    if not book_name:
        print("书籍名称不能为空!")
        return

    # 创建下载目录
    download_dir = "../downloaded_books"
    os.makedirs(download_dir, exist_ok=True)

    # 搜索书籍
    print(f"正在搜索 '{book_name}'...")
    results = zlib.search_books(book_name)

    if not results:
        print("没有找到相关书籍")
        return

    print("\n找到以下结果:")
    for i, book in enumerate(results, 1):
        print(f"{i}. {book['title']} - {book['authors']} ({book['extension'].upper()}, {book['filesize']})")

    while True:
        choice = input("\n请输入要下载的书籍编号 (或输入q退出): ").strip()
        if choice.lower() == 'q':
            return

        try:
            choice = int(choice) - 1
            if choice < 0 or choice >= len(results):
                print("无效的选择!")
                continue

            selected_book = results[choice]
            print(f"\n准备下载: {selected_book['title']}")
            print(f"作者: {selected_book['authors']}")
            print(f"格式: {selected_book['extension'].upper()}")
            print(f"大小: {selected_book['filesize']}")

            # 下载书籍
            print("开始下载...")
            downloaded_path = zlib.download_book(selected_book['download_link'], download_dir)

            if downloaded_path:
                print(f"\n下载完成! 文件保存在: {downloaded_path}")
            else:
                print("下载失败")

            # 询问是否继续下载其他书籍
            another = input("\n是否要继续下载其他书籍? (y/n): ").strip().lower()
            if another != 'y':
                break

        except ValueError:
            print("请输入有效的数字!")
        except Exception as e:
            print(f"发生错误: {e}")


if __name__ == "__main__":
    main()