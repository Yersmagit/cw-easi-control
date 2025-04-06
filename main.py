import logging
import time
from pathlib import Path
import json
import shutil
import psutil
from datetime import datetime
from .ClassWidgets.base import PluginBase

class Plugin(PluginBase):
    def __init__(self, cw_contexts, method):
        # 先初始化路径属性
        self.plugin_dir = Path(__file__).parent  # 必须放在最前面
        self.base_dir = Path(cw_contexts.get('BASE_DIRECTORY', '.'))
        self.config_path = self.base_dir / 'config' / 'widget.json'
        self.backup_path = self.plugin_dir / 'widget_backup.json'
        
        # 再调用父类初始化
        super().__init__(cw_contexts, method)
        
        # 最后初始化其他依赖
        self._init_logger()
        self.logger = logging.getLogger(__name__)
        
        # 状态管理系统
        self.state = {
            'process_name': 'lx-music-desktop',
            'modified': False,
            'backup_valid': False,
            'last_check': 0,
            'check_interval': 1
        }

        self._verify_permissions()
        self.logger.info("插件初始化完成")

    def _init_logger(self):
        """修复日志初始化顺序"""
        logger = logging.getLogger(__name__)
        if logger.handlers:
            return

        # 使用已经初始化的plugin_dir属性
        log_dir = self.plugin_dir / "log"
        try:
            log_dir.mkdir(exist_ok=True, mode=0o755)
        except Exception as e:
            print(f"无法创建日志目录: {str(e)}")
            return

        log_file = log_dir / f"plugin_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        file_handler = logging.FileHandler(
            filename=log_file,
            encoding='utf-8',
            mode='a'
        )
        file_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.propagate = False

    def _verify_permissions(self):
        """系统权限验证"""
        try:
            # 配置文件读取测试
            with open(self.config_path, 'r'):
                pass
            self.logger.info("配置文件读取权限验证通过")
            
            # 插件目录写入测试
            test_file = self.plugin_dir / "perm_test.tmp"
            test_file.touch()
            test_file.unlink()
            self.logger.info("插件目录写入权限正常")
            
            # 备份文件检查
            if self.backup_path.exists():
                self.logger.warning("检测到已存在的备份文件")
                
        except PermissionError:
            self.logger.critical("权限不足，请以管理员权限运行主程序")
        except Exception as e:
            self.logger.error(f"权限验证失败: {str(e)}")

    def _detect_process(self):
        """增强型进程检测"""
        if time.time() - self.state['last_check'] < self.state['check_interval']:
            return self.state['process_found']
        
        self.state['last_check'] = time.time()
        target = self.state['process_name'].lower()
        process_found = False

        try:
            self.logger.debug("开始进程扫描...")
            for proc in psutil.process_iter(['name', 'pid', 'status']):
                proc_name = proc.info['name'] or ''
                if target in proc_name.lower():
                    self.logger.debug(f"匹配进程: {proc_name} (PID={proc.info['pid']})")
                    process_found = True
                    break

            # 记录状态变化
            if process_found != self.state.get('process_found', False):
                status = "出现" if process_found else "消失"
                self.logger.info(f"进程状态变化: {status}")
                
            self.state['process_found'] = process_found
            return process_found
            
        except Exception as e:
            self.logger.error(f"进程检测异常: {str(e)}")
            return False

    def _create_backup(self):
        """创建可靠配置备份"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as src:
                original_data = json.load(src)
                widgets = original_data.get('widgets', [])
                
                if not widgets:
                    self.logger.error("配置无效：无widgets列表")
                    return False
                    
                self.state['original_value'] = widgets[-1]
                
                with open(self.backup_path, 'w', encoding='utf-8') as dst:
                    json.dump(original_data, dst, indent=4, ensure_ascii=False)
                    
                self.logger.info(f"配置备份成功，最后项: {self.state['original_value']}")
                self.state['backup_valid'] = True
                return True
                
        except Exception as e:
            self.logger.error(f"备份失败: {str(e)}")
            self.state['backup_valid'] = False
            return False

    def _apply_modification(self):
        """安全应用配置修改"""
        if not self.state['backup_valid']:
            self.logger.warning("无效备份，拒绝修改")
            return False

        try:
            with open(self.config_path, 'r+', encoding='utf-8') as f:
                data = json.load(f)
                current_value = data['widgets'][-1]
                
                if current_value == "lx-music-lyrics.ui":
                    self.logger.debug("配置已是目标状态")
                    return True
                    
                data['widgets'][-1] = "lx-music-lyrics.ui"
                f.seek(0)
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.truncate()
                
                self.logger.info(f"配置修改成功: {current_value} → lx-music-lyrics.ui")
                return True
                
        except Exception as e:
            self.logger.error(f"修改失败: {str(e)}")
            return False

    def _restore_config(self):
        """可靠配置恢复"""
        if not self.backup_path.exists():
            self.logger.error("备份文件丢失，无法恢复")
            return False

        try:
            with open(self.backup_path, 'r', encoding='utf-8') as src:
                backup_data = json.load(src)
                original_value = backup_data['widgets'][-1]
                
                with open(self.config_path, 'w', encoding='utf-8') as dst:
                    json.dump(backup_data, dst, indent=4, ensure_ascii=False)
                    
                self.logger.info(f"配置恢复成功: {original_value}")
                self.state['modified'] = False
                self.state['backup_valid'] = False
                return True
                
        except Exception as e:
            self.logger.error(f"恢复失败: {str(e)}")
            return False

    def update(self, cw_contexts):
        """主状态机逻辑"""
        super().update(cw_contexts)
        
        # 进程检测
        process_running = self._detect_process()
        
        # 状态处理：进程启动
        if process_running and not self.state['modified']:
            self.logger.info("检测到目标进程，开始配置修改流程")
            if self._create_backup() and self._apply_modification():
                self.state['modified'] = True
                self.logger.info("配置修改流程完成")
            else:
                self.logger.error("配置修改流程失败")

        # 状态处理：进程退出
        if not process_running and self.state['modified']:
            self.logger.info("目标进程已退出，开始恢复配置")
            if self._restore_config():
                self.logger.info("配置恢复流程完成")
            else:
                self.logger.error("配置恢复流程失败")