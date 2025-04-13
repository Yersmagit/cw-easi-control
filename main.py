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
        # 初始化路径属性（必须最先执行）
        self.plugin_dir = Path(__file__).parent
        self.config_dir = self.plugin_dir / "config"
        self.log_dir = self.plugin_dir / "log"
        
        # 创建必要目录
        self.config_dir.mkdir(exist_ok=True, parents=True)
        self.log_dir.mkdir(exist_ok=True, parents=True)
        
        # 配置文件路径
        self.state_file = self.config_dir / "plugin_state.json"
        self.original_file = self.config_dir / "original_value.txt"
        self.base_dir = Path(cw_contexts.get('BASE_DIRECTORY', '.'))
        self.target_config = self.base_dir / "config" / "widget.json"
        
        # 调用父类初始化
        super().__init__(cw_contexts, method)
        
        # 初始化日志系统
        self._init_logger()
        self.logger = logging.getLogger(__name__)
        
        # 状态管理系统
        self.state = {
            'process_name': 'lx-music-desktop.exe',
            'modified': False,
            'original_value': None,
            'backup_done': False
        }
        self._load_state()
        self._migrate_old_files()  # 旧文件迁移
        
        self.logger.info("插件初始化完成")

    def _init_logger(self):
        """日志系统初始化"""
        logger = logging.getLogger(__name__)
        if logger.handlers:
            return

        file_handler = logging.FileHandler(
            filename=self.log_dir / f"plugin_{datetime.now().strftime('%Y-%m-%d')}.log",
            encoding='utf-8'
        )
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)

    def _migrate_old_files(self):
        """旧配置文件迁移"""
        old_files = [
            (self.plugin_dir / "plugin_state.json", self.state_file),
            (self.plugin_dir / "original_value.txt", self.original_file)
        ]
        
        for old_path, new_path in old_files:
            if old_path.exists() and not new_path.exists():
                try:
                    old_path.rename(new_path)
                    self.logger.info(f"迁移旧配置文件: {old_path.name}")
                except Exception as e:
                    self.logger.error(f"文件迁移失败: {str(e)}")

    def _load_state(self):
        """加载持久化状态"""
        try:
            # 加载状态文件
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    saved_state = json.load(f)
                    self.state.update({
                        'modified': saved_state.get('modified', False),
                        'backup_done': saved_state.get('backup_done', False)
                    })
            
            # 加载原始值
            if self.original_file.exists():
                with open(self.original_file, 'r') as f:
                    self.state['original_value'] = f.read().strip()
                    
        except Exception as e:
            self.logger.error(f"状态加载失败: {str(e)}")

    def _save_state(self):
        """保存持久化状态"""
        try:
            state_to_save = {
                'modified': self.state['modified'],
                'backup_done': self.state['backup_done']
            }
            with open(self.state_file, 'w') as f:
                json.dump(state_to_save, f)
            
            if self.state['original_value']:
                with open(self.original_file, 'w') as f:
                    f.write(self.state['original_value'])
                    
        except Exception as e:
            self.logger.error(f"状态保存失败: {str(e)}")

    def _detect_process(self):
        """精确进程检测"""
        try:
            target = self.state['process_name'].lower()
            return any(
                proc.info.get('name', '').lower() == target
                for proc in psutil.process_iter(['name'])
            )
        except Exception as e:
            self.logger.error(f"进程检测失败: {str(e)}")
            return False

    def _create_backup(self):
        """创建唯一备份"""
        if self.state['backup_done']:
            return True
            
        try:
            with open(self.target_config, 'r') as f:
                data = json.load(f)
                original = data.get('widgets', [])[-1] if data.get('widgets') else None
                
                if not original:
                    self.logger.error("无效的widgets配置")
                    return False
                
                with open(self.original_file, 'w') as f:
                    f.write(original)
                self.state.update({
                    'original_value': original,
                    'backup_done': True
                })
                self._save_state()
                return True
                
        except Exception as e:
            self.logger.error(f"备份失败: {str(e)}")
            return False

    def _apply_modification(self):
        """应用配置修改"""
        if not self._create_backup():
            return False

        try:
            with open(self.target_config, 'r+') as f:
                data = json.load(f)
                if data['widgets'][-1] == "lx-music-lyrics.ui":
                    return True
                    
                data['widgets'][-1] = "lx-music-lyrics.ui"
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
                
                self.state['modified'] = True
                self._save_state()
                return True
                
        except Exception as e:
            self.logger.error(f"修改失败: {str(e)}")
            return False

    def _restore_config(self):
        """恢复原始配置"""
        if not self.original_file.exists():
            self.logger.error("原始值备份丢失")
            return False

        try:
            with open(self.original_file, 'r') as f:
                original_value = f.read().strip()
                
            with open(self.target_config, 'r+') as f:
                data = json.load(f)
                if data['widgets'][-1] == original_value:
                    return True
                    
                data['widgets'][-1] = original_value
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
                
                self.state.update({
                    'modified': False,
                    'backup_done': False
                })
                self._save_state()
                self.original_file.unlink(missing_ok=True)
                return True
                
        except Exception as e:
            self.logger.error(f"恢复失败: {str(e)}")
            return False

    def update(self, cw_contexts):
        """主状态机逻辑"""
        super().update(cw_contexts)
        
        process_running = self._detect_process()
        
        # 进程启动处理
        if process_running and not self.state['modified']:
            if self._apply_modification():
                self.logger.info("配置修改成功")
                
        # 进程退出处理
        if not process_running and self.state['modified']:
            if self._restore_config():
                self.logger.info("配置恢复成功")