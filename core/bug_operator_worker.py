# core/bug_operator_worker.py - BUG操作工作线程

import os
import sys
import re
import time
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from PyQt5.QtCore import QThread, pyqtSignal
from config.settings import EDGEDRIVER_PATH, ZEN_TAO_BASE_URL


class BugOperatorWorker(QThread):
    """BUG操作工作线程 - 无头模式"""

    log_signal = pyqtSignal(str, bool)  # message, is_error
    bugs_data_signal = pyqtSignal(list)  # 发送BUG数据列表
    operation_result_signal = pyqtSignal(bool, str)  # 操作结果
    finished_signal = pyqtSignal(bool, str)  # 完成信号

    def __init__(self, manager_account, manager_password, operator_name, operation_type, query_params=None,
                 operation_params=None):
        super().__init__()
        self.manager_account = manager_account
        self.manager_password = manager_password
        self.operator_name = operator_name
        self.operation_type = operation_type  # 'query' or 'execute'
        self.query_params = query_params or {}
        self.operation_params = operation_params or {}
        self.base_url = ZEN_TAO_BASE_URL
        self.driver = None

    def run(self):
        """主执行逻辑"""
        try:
            self.log_signal.emit("初始化无头浏览器...", False)

            if not self._setup_driver():
                self.finished_signal.emit(False, "浏览器启动失败")
                return

            self.log_signal.emit("浏览器启动成功", False)

            if not self._login():
                self.finished_signal.emit(False, "管理员登录失败")
                return

            self.log_signal.emit("管理员登录成功", False)
            self._log_admin_operation("管理员登录用于BUG操作")

            if self.operation_type == 'query':
                self._execute_query()
            elif self.operation_type == 'execute':
                self._execute_operation()
            else:
                self.finished_signal.emit(False, f"未知操作类型: {self.operation_type}")

        except Exception as e:
            self.log_signal.emit(f"BUG操作异常: {e}", True)
            self.log_signal.emit(traceback.format_exc(), True)
            self.finished_signal.emit(False, f"操作异常: {e}")
        finally:
            self._cleanup()

    def _setup_driver(self):
        """设置浏览器驱动 - 无头模式"""
        try:
            edge_options = EdgeOptions()
            # 强制使用无头模式
            edge_options.add_argument("--headless")
            edge_options.add_argument("--no-sandbox")
            edge_options.add_argument("--disable-dev-shm-usage")
            edge_options.add_argument("--window-size=1920,1080")
            edge_options.add_argument("--disable-gpu")
            edge_options.add_argument("--disable-blink-features=AutomationControlled")
            edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            edge_options.add_experimental_option('useAutomationExtension', False)

            # 设置用户代理
            edge_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

            if EDGEDRIVER_PATH and os.path.exists(EDGEDRIVER_PATH):
                service = EdgeService(executable_path=EDGEDRIVER_PATH)
                self.driver = webdriver.Edge(service=service, options=edge_options)
            else:
                self.driver = webdriver.Edge(options=edge_options)

            # 隐藏自动化标识
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10)
            return True

        except Exception as e:
            self.log_signal.emit(f"浏览器初始化失败: {e}", True)
            return False

    def _login(self):
        """登录禅道"""
        try:
            self.driver.get(f"{self.base_url}/user-login.html")

            # 等待登录页面加载
            wait = WebDriverWait(self.driver, 15)
            account_input = wait.until(EC.element_to_be_clickable((By.ID, 'account')))
            password_input = wait.until(EC.element_to_be_clickable((By.NAME, 'password')))

            # 输入账号密码
            account_input.clear()
            account_input.send_keys(self.manager_account)

            password_input.clear()
            password_input.send_keys(self.manager_password)

            # 点击登录
            login_button = wait.until(EC.element_to_be_clickable((By.ID, 'submit')))
            login_button.click()

            # 等待登录完成
            wait.until(
                EC.any_of(
                    EC.url_changes(f"{self.base_url}/user-login.html"),
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.main-header'))
                )
            )

            # 检查登录结果
            if "登录失败" in self.driver.page_source or "user-login" in self.driver.current_url:
                return False

            return True

        except Exception as e:
            self.log_signal.emit(f"登录异常: {e}", True)
            return False

    def _execute_query(self):
        """执行BUG查询"""
        try:
            project_name = self.query_params.get('project_name', '')

            # 查找项目ID
            print(f'---------------debug-111111111111----------{project_name}')
            project_id = self._find_project_id(project_name)
            if not project_id:
                self.finished_signal.emit(False, f"未找到产品: {project_name}")
                return

            self.log_signal.emit(f"找到产品ID: {project_id}", False)

            # 导航到BUG页面
            #project-bug-2242-status,id_desc-0-all.html
            bug_url = f"{self.base_url}/project-bug-{project_id}-resolution_asc-0-all-0--2000-1.html"
            self.driver.get(bug_url)

            # 等待页面加载
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            # 应用查询条件
            self._apply_query_filters()

            # 解析BUG列表
            bugs_data = self._parse_bug_list()
            print(f'bugs_data:{bugs_data}')

            if bugs_data:
                self.bugs_data_signal.emit(bugs_data)
                self.finished_signal.emit(True, f"查询完成，找到 {len(bugs_data)} 个BUG")
            else:
                self.finished_signal.emit(False, "未查询到任何BUG数据")

        except Exception as e:
            self.log_signal.emit(f"查询BUG失败: {e}", True)
            self.finished_signal.emit(False, f"查询失败: {e}")

    def _execute_operation(self):
        """执行BUG操作"""
        try:
            bug_id = self.operation_params.get('bug_id')
            action = self.operation_params.get('action')
            comment = self.operation_params.get('comment')

            self.log_signal.emit(f"正在执行操作: {action} - BUG ID: {bug_id}", False)

            # 导航到BUG详情页
            bug_detail_url = f"{self.base_url}/bug-view-{bug_id}.html"
            self.driver.get(bug_detail_url)

            # 等待页面加载
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )

            # 根据操作类型执行相应操作
            success = False
            if action == "关闭BUG":
                success = self._close_bug(bug_id, comment)
            elif action == "激活BUG":
                success = self._activate_bug(bug_id, comment)
            elif action == "解决BUG":
                success = self._resolve_bug(bug_id, comment)
            elif action == "指派BUG":
                success = self._assign_bug(bug_id, comment)
            else:
                self.operation_result_signal.emit(False, f"不支持的操作类型: {action}")
                return

            if success:
                self._log_admin_operation(f"BUG操作: {action} - BUG ID: {bug_id}")
                self.operation_result_signal.emit(True, f"BUG {bug_id} {action}操作成功")
                self.finished_signal.emit(True, f"操作成功完成")
            else:
                self.operation_result_signal.emit(False, f"BUG {bug_id} {action}操作失败")
                self.finished_signal.emit(False, f"操作失败")

        except Exception as e:
            self.log_signal.emit(f"执行BUG操作失败: {e}", True)
            self.operation_result_signal.emit(False, f"操作异常: {e}")
            self.finished_signal.emit(False, f"操作异常: {e}")

    def _find_project_id(self, project_name):
        """查找项目ID"""
        try:
            # 导航到产品列表
            self.driver.get(os.path.join(os.getcwd(),"demo.html"))
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="project-view"]'))
            )
            # 查找所有匹配关键字的 <tr>
            print(f"project_name:{project_name}")
            matching_trs = self.driver.find_elements(
                By.XPATH, f"//tr[.//*[contains(text(), '{project_name}') or contains(@title, '{project_name}')]]"
            )
            print('matching_trs',matching_trs)
            for tr in matching_trs:
                data_id = tr.get_attribute("data-id")
                href = tr.find_element(By.XPATH, ".//a[contains(@href, 'project-view-')]").get_attribute("href")
                project_id = re.search(r"project-view-(\d+)", href).group(1)
                print(data_id)
            return project_id


                # # 如果是 <a> 标签，提取 href
                # if element.tag_name == "a":
                #     href = element.get_attribute("href")
                #     print("URL:", href)  # 如 "/zentao/project-view-2242.html"

        except Exception as e:
            self.log_signal.emit(f"查找产品ID失败: {e}", True)
            return None

    def _apply_query_filters(self):
        """应用查询过滤条件"""
        try:
            # 这里可以根据assigned_to和solution参数设置过滤条件
            # 由于禅道的界面可能有所不同，需要根据实际情况调整选择器
            assigned_to = self.query_params.get('assigned_to', 'all')
            if assigned_to != 'all':
                # 尝试找到状态过滤器并设置
                try:
                    assigned_to_select = self.driver.find_element(By.NAME, 'assigned_to')
                    Select(assigned_to_select).select_by_value(assigned_to)
                    self.log_signal.emit(f"已设置分配过滤: {assigned_to}", False)
                except:
                    pass

            solution = self.query_params.get('solution', 'all')
            if solution != 'all':
                # 尝试找到严重程度过滤器并设置
                try:
                    solution_select = self.driver.find_element(By.NAME, 'solution')
                    Select(solution_select).select_by_value(solution)
                    self.log_signal.emit(f"已设置解决方案过滤: {solution}", False)
                except:
                    pass

        except Exception as e:
            self.log_signal.emit(f"应用查询过滤器失败: {e}", True)

    def _parse_bug_list(self):
        """解析BUG列表"""
        print(self.driver.page_source)
        try:
            bugs_data = []
            # 查找BUG列表表格
            table_selectors = [
                'table.table',
                '#bugList table',
                'main-table',
                'table'
            ]

            table = None
            for selector in table_selectors:
                try:
                    table = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print('table:', table)
                    if table:
                        break
                except:
                    continue

            if not table:
                self.log_signal.emit("未找到BUG列表表格", True)
                return bugs_data

            # 解析表格行
            rows = table.find_elements(By.TAG_NAME, 'tr')[1:]  # 跳过标题行
            print(f"表格行数(不含标题): {len(rows)}")

            # 预先获取过滤参数，避免在循环中重复获取
            assigned_to_filter = self.query_params.get('assigned_to', '全部')
            solution_filter = self.query_params.get('solution', '全部')
            bug_id_filter = self.query_params.get('bug_id', '')

            is_method1 = bool(assigned_to_filter not in ('all', '') and solution_filter not in ('all', ''))
            is_method2 = bool(bug_id_filter)

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, 'td')
                print(f"行单元格数: {len(cells)}")
                print(f'----1111111111111111111111111111111--------------')
                if len(cells) >= 6:  # 确保有足够的列
                    try:
                        bug_info = {
                            'id': self._extract_bug_id(cells[0]),
                            'title': cells[3].text.strip() if len(cells) > 1 else '',
                            'status': cells[1].text.strip() if len(cells) > 2 else '',
                            'opened_by': cells[4].text.strip() if len(cells) > 4 else '',
                            'assigned_to': cells[5].text.strip() if len(cells) > 5 else '',
                            'solution': cells[7].text.strip() if len(cells) > 6 else ''
                        }
                        print('----------------------222222222222222222222222-------------------------')
                        print(cells[0].text.strip(), cells[1].text.strip(), cells[2].text.strip(),
                              cells[3].text.strip(), cells[4].text.strip(), cells[5].text.strip(),
                              cells[6].text.strip(), cells[7].text.strip(), cells[8].text.strip())

                        # 仅当有有效ID时进行处理
                        if bug_info['id']:
                            print('------2222222----',is_method1,is_method2)
                            if is_method1:
                                print('----333333------',bug_info['assigned_to'],bug_info['solution'])
                                print('----44444444------', type(bug_info['assigned_to']), type(bug_info['solution']))
                                # 修正：直接使用 bug_info 字典中的值进行判断
                                if assigned_to_filter == '全部' and solution_filter == '全部':
                                    bugs_data.append(bug_info)
                                elif bug_info['assigned_to'] == assigned_to_filter and bug_info['solution'] == solution_filter:
                                    print('-----5555555555-------')
                                    bugs_data.append(bug_info)
                            elif is_method2:
                                # 修正：直接使用 bug_info 字典中的值进行判断
                                if  str(bug_info['id']) == bug_id_filter:
                                    bugs_data.append(bug_info)
                            else:
                                # 默认情况下，如果没有特定的过滤方式，则全部添加
                                bugs_data.append(bug_info)
                    except Exception as e:
                        self.log_signal.emit(f"解析BUG行失败: {e}", True)
                        continue

            return bugs_data

        except Exception as e:
            self.log_signal.emit(f"解析BUG列表失败: {e}", True)
            return []

    def _extract_bug_id(self, cell):
        """从单元格中提取BUG ID"""
        try:
            # 尝试从链接中提取ID
            link = cell.find_element(By.TAG_NAME, 'a')
            href = link.get_attribute('href')
            print(f"提取BUG ID，链接: {href}")
            if href:
                # 从URL中提取ID
                parts = href.split('-')
                for part in parts:
                    if part.isdigit():
                        return part

            # 如果没有链接，直接取文本
            text = cell.text.strip()
            if text.isdigit():
                return text

        except:
            # 如果提取失败，返回单元格文本
            text = cell.text.strip()
            # 提取数字部分
            import re
            numbers = re.findall(r'\d+', text)
            if numbers:
                return numbers[0]

        return ""

    def _close_bug(self, bug_id, comment):
        """关闭BUG"""
        try:
            # 查找关闭按钮
            close_button_selectors = [
                'a[href*="bug-close"]',
                '.btn:contains("关闭")',
                'button:contains("关闭")'
            ]

            close_button = None
            for selector in close_button_selectors:
                try:
                    if ':contains(' in selector:
                        # 使用XPath查找包含文本的元素
                        xpath = f"//a[contains(text(),'关闭')] | //button[contains(text(),'关闭')]"
                        close_button = self.driver.find_element(By.XPATH, xpath)
                    else:
                        close_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if close_button:
                        break
                except:
                    continue

            if not close_button:
                self.log_signal.emit("未找到关闭按钮", True)
                return False

            close_button.click()

            # 等待关闭页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'form'))
            )

            # 填写备注
            return self._fill_comment_and_submit(comment)

        except Exception as e:
            self.log_signal.emit(f"关闭BUG失败: {e}", True)
            return False

    def _activate_bug(self, bug_id, comment):
        """激活BUG"""
        try:
            # 查找激活按钮
            activate_button_selectors = [
                'a[href*="bug-activate"]',
                '.btn:contains("激活")',
                'button:contains("激活")'
            ]

            activate_button = None
            for selector in activate_button_selectors:
                try:
                    if ':contains(' in selector:
                        xpath = f"//a[contains(text(),'激活')] | //button[contains(text(),'激活')]"
                        activate_button = self.driver.find_element(By.XPATH, xpath)
                    else:
                        activate_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if activate_button:
                        break
                except:
                    continue

            if not activate_button:
                self.log_signal.emit("未找到激活按钮", True)
                return False

            activate_button.click()

            # 等待激活页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'form'))
            )

            # 填写备注
            return self._fill_comment_and_submit(comment)

        except Exception as e:
            self.log_signal.emit(f"激活BUG失败: {e}", True)
            return False

    def _resolve_bug(self, bug_id, comment):
        """解决BUG"""
        try:
            # 查找解决按钮
            resolve_button_selectors = [
                'a[href*="bug-resolve"]',
                '.btn:contains("解决")',
                'button:contains("解决")'
            ]

            resolve_button = None
            for selector in resolve_button_selectors:
                try:
                    if ':contains(' in selector:
                        xpath = f"//a[contains(text(),'解决')] | //button[contains(text(),'解决')]"
                        resolve_button = self.driver.find_element(By.XPATH, xpath)
                    else:
                        resolve_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if resolve_button:
                        break
                except:
                    continue

            if not resolve_button:
                self.log_signal.emit("未找到解决按钮", True)
                return False

            resolve_button.click()

            # 等待解决页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'form'))
            )

            # 填写备注
            return self._fill_comment_and_submit(comment)

        except Exception as e:
            self.log_signal.emit(f"解决BUG失败: {e}", True)
            return False

    def _assign_bug(self, bug_id, comment):
        """指派BUG"""
        try:
            # 查找指派按钮
            assign_button_selectors = [
                'a[href*="bug-assignTo"]',
                '.btn:contains("指派")',
                'button:contains("指派")'
            ]

            assign_button = None
            for selector in assign_button_selectors:
                try:
                    if ':contains(' in selector:
                        xpath = f"//a[contains(text(),'指派')] | //button[contains(text(),'指派')]"
                        assign_button = self.driver.find_element(By.XPATH, xpath)
                    else:
                        assign_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if assign_button:
                        break
                except:
                    continue

            if not assign_button:
                self.log_signal.emit("未找到指派按钮", True)
                return False

            assign_button.click()

            # 等待指派页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'form'))
            )

            # 填写备注
            return self._fill_comment_and_submit(comment)

        except Exception as e:
            self.log_signal.emit(f"指派BUG失败: {e}", True)
            return False

    def _fill_comment_and_submit(self, comment):
        """填写备注并提交"""
        try:
            # 查找备注输入框
            comment_selectors = [
                'textarea[name="comment"]',
                'textarea[name="remark"]',
                'textarea[name="note"]',
                '#comment',
                '#remark',
                '#note'
            ]

            comment_field = None
            for selector in comment_selectors:
                try:
                    comment_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if comment_field:
                        break
                except:
                    continue

            if comment_field:
                comment_field.clear()
                comment_field.send_keys(comment)
                self.log_signal.emit("已填写操作备注", False)
            else:
                self.log_signal.emit("未找到备注输入框", True)

            # 查找并点击提交按钮
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                '.btn-primary',
                '.btn-success',
                'button:contains("提交")',
                'button:contains("保存")'
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    if ':contains(' in selector:
                        xpath = f"//button[contains(text(),'提交')] | //button[contains(text(),'保存')] | //input[@value='提交'] | //input[@value='保存']"
                        submit_button = self.driver.find_element(By.XPATH, xpath)
                    else:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if submit_button:
                        break
                except:
                    continue

            if not submit_button:
                self.log_signal.emit("未找到提交按钮", True)
                return False

            submit_button.click()

            # 等待提交完成
            time.sleep(2)

            # 检查是否提交成功（可以根据页面变化或成功消息判断）
            if "成功" in self.driver.page_source or "success" in self.driver.current_url.lower():
                self.log_signal.emit("操作提交成功", False)
                return True
            else:
                self.log_signal.emit("操作可能未成功提交", True)
                return True  # 假设成功，因为没有明确的失败标识

        except Exception as e:
            self.log_signal.emit(f"填写备注并提交失败: {e}", True)
            return False

    def _log_admin_operation(self, operation_type):
        """记录管理员操作日志"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_content = f"[{timestamp}] 管理员账号 {self.manager_account} 被操作人 {self.operator_name} 用于 {operation_type}\n"

            # 创建日志目录
            log_dir = os.path.join(os.getcwd(), "logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # 写入操作日志
            log_file = os.path.join(log_dir, "admin_operations.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_content)

            self.log_signal.emit(f"管理员操作已记录: {operation_type}", False)

        except Exception as e:
            self.log_signal.emit(f"记录管理员操作失败: {e}", True)

    def _cleanup(self):
        """清理资源"""
        if self.driver:
            try:
                self.driver.quit()
                self.log_signal.emit("浏览器已关闭", False)
            except:
                pass
            finally:
                self.driver = None
