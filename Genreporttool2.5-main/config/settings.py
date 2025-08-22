# config/settings.py
import os

class ManagerAccountConfig:
    """管理员账号配置"""

    def __init__(self):
        self.account = "zhouxuebo"
        self.password = "Abcdef01"
        self.is_configured = False

# 定义默认下载目录为程序运行目录下的 'raw_data'
# 确保在 main.py 中将当前工作目录设置为脚本所在目录，以保证相对路径正确
DOWNLOAD_DIR = os.path.join(os.getcwd(), "raw_data")
#doc的默认路径：
Doc1_defaut_path = os.path.join(os.getcwd(), "raw_data")
Doc2_defaut_path = os.path.join(os.getcwd(), "raw_data")
Doc3_defaut_path = os.path.join(os.getcwd(), "raw_data")
Doc4_defaut_path = os.path.join(os.getcwd(), "raw_data")


#台账和标准模板信息：
Reference_msg_path = os.path.join(os.getcwd(), "taizhang")
Testreport_path = os.path.join(os.getcwd(),"")
# 禅道URL基地址
ZEN_TAO_BASE_URL = "http://10.200.10.220/zentao" #



# Edge WebDriver 的路径
# 请将 msedgedriver.exe 放在项目根目录，或者在此处指定其完整路径
# 确保 msedgedriver 的版本与您的 Edge 浏览器版本兼容
EDGEDRIVER_PATH = None
# 如果 msedgedriver.exe 不在项目根目录，请提供完整路径，例如：
# EDGEDRIVER_PATH = "C:\\path\\to\\your\\msedgedriver.exe"

# 默认无头模式设置 (True: 默认无头，不显示浏览器界面；False: 默认有头，显示浏览器界面)
HEADLESS_MODE_DEFAULT = True # 默认勾选无头模式

# 默认测试单号 (如果settings.json中没有保存，则使用此默认值)
TEST_REPORT_ID_DEFAULT = None# 截图中的默认值

MANAGER_CONFIG = ManagerAccountConfig()

# BUG查询相关配置
BUG_QUERY_STATUS_OPTIONS = [
    "all", "active", "resolved", "closed"
]

BUG_SEVERITY_OPTIONS = [
    "1", "2", "3", "4"  # 1-严重，2-主要，3-次要，4-建议
]

# BUG交互操作相关配置
BUG_INTERACTIVE_CONFIG = {
    "check_comment_interval": 1000,  # 检查备注间隔(毫秒)
    "highlight_duration": 3000,      # 字段高亮持续时间(毫秒)
    "auto_save_interval": 30000,     # 自动保存间隔(毫秒)
    "session_timeout": 3600,         # 会话超时时间(秒)
}

# 内网环境优化配置
INTRANET_OPTIMIZATION = {
    "enabled": True,                  # 是否启用内网优化
    "login_wait_time": 1,            # 登录等待时间(秒) - 极致减少
    "page_load_wait_time": 1,        # 页面加载等待时间(秒) - 极致减少
    "element_wait_time": 0.5,        # 元素查找等待时间(秒) - 极致减少
    "download_check_interval": 0.01, # 下载检查间隔(秒) - 极致减少
    "file_stabilize_checks": 2,      # 文件大小稳定检查次数 - 极致减少
    "retry_count": 2,                # 重试次数 - 极致减少
    "retry_interval": 0.01,          # 重试间隔(秒) - 极致减少
    
    # 新增："看到就立即操作"策略参数
    "aggressive_mode": True,          # 是否启用激进模式（看到就立即操作）
    "max_attempts": 100,             # 最大尝试次数 - 大幅增加
    "attempt_interval": 0.01,        # 尝试间隔(秒) - 极致减少
    "immediate_action": True,        # 是否启用立即操作模式
    
    # 新增："瞬间响应"策略参数
    "instant_response": True,         # 是否启用瞬间响应模式
    "ultra_aggressive": True,        # 是否启用超激进模式
    "zero_delay": True,              # 是否启用零延迟模式
    
    # 新增："可操作即操作"策略参数
    "actionable_operation": True,     # 是否启用可操作即操作模式
    "input_test": True,              # 是否启用输入测试模式
    "element_validation": True,      # 是否启用元素验证模式
    "ultra_fast_polling": True,      # 是否启用超快轮询模式
    
    # 新增："人类看到就能操作"策略参数
    "human_like_operation": True,     # 是否启用人类式操作模式
    "instant_element_detection": True, # 是否启用瞬间元素检测
    "no_page_load_wait": True,       # 是否不等待页面完全加载
    
    # 新增："看到就立即操作"策略参数
    "see_and_operate": True,          # 是否启用看到就立即操作模式
    "ultra_fast_detection": True,     # 是否启用超快检测模式
    "no_visibility_check": True,      # 是否不检查元素可见性
}

# 操作日志配置
OPERATION_LOG_CONFIG = {
    "log_file": "logs/admin_operations.log",
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5,
    "log_format": "[%(asctime)s] %(levelname)s - %(message)s"
}

