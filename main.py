import logging
import time
from pathlib import Path
import json
import shutil
import psutil
from datetime import datetime
from .ClassWidgets.base import PluginBase


# --常量定义--

# 用于显示特定小组件的课程名称，如"课间", "暂无课程", "自习"
LESSON_TRIGGERS = ["Subject_1", "Subiect_2", "Subiect_3"]  # 可扩展的触发文本列表
# 在上述特定课程切换的小组件名称。当课程为 LESSON_TRIGGERS 中的课程时，显示目标组件；否则，显示原始组件
WIDGET_TARGET_PAIR = ("example-1.ui", "example-2.ui")  # (原始组件，目标组件)


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
            'backup_done': False,
            'check_interval': 3,  # 从5秒改为3秒
            'lesson_modified': False,
            'lesson_backup_done': False,
            'lesson_original_value': None,
            'last_lesson_change': 0,
            'current_lesson': None
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
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    saved_state = json.load(f)
                    self.state.update({
                        'modified': saved_state.get('modified', False),
                        'backup_done': saved_state.get('backup_done', False),
                        'lesson_modified': saved_state.get('lesson_modified', False),
                        'lesson_backup_done': saved_state.get('lesson_backup_done', False)
                    })
            
            # 加载原始值
            if self.original_file.exists():
                with open(self.original_file, 'r') as f:
                    self.state['original_value'] = f.read().strip()

            # 加载课程相关备份
            lesson_backup = self.config_dir / "lesson_backup.json"
            if lesson_backup.exists():
                with open(lesson_backup, 'r') as f:
                    self.state['lesson_original_value'] = json.load(f).get('widgets', [])
                    
        except json.JSONDecodeError as e:
            self.logger.critical(f"状态文件损坏，重置状态: {str(e)}")
            self._reset_state()

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
            current_time = time.time()
            target = self.state['process_name'].lower()
            
            # 使用state中的间隔参数
            if current_time - self.state.get('last_check', 0) < self.state['check_interval']:
                return self.state.get('process_running', False)
            
            # 执行实际进程检测
            process_running = False
            for proc in psutil.process_iter(['name']):
                proc_name = proc.info['name'].lower()
                if proc_name == target:
                    process_running = True
                    break
            
            # 更新状态
            self.state['last_check'] = current_time
            self.state['process_running'] = process_running
            return process_running
            
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

        # 新功能：课程变化检测
        current_lesson = self._check_lesson_change()
        lesson_condition = self._lesson_condition_met()
        time_since_change = time.time() - self.state['last_lesson_change']
        
        # 课程相关处理逻辑
        if time_since_change > 4:  # 等待4秒防抖动
            if lesson_condition and not self.state['lesson_modified']:
                if self._modify_for_lesson():
                    self.logger.info("课程条件触发修改完成")
                    
            elif not lesson_condition and self.state['lesson_modified']:
                if self._restore_for_lesson():
                    self.logger.info("课程条件触发恢复完成")
        
        # 进程启动处理
        if process_running and not self.state['modified']:
            if self._apply_modification():
                self.logger.info("配置修改成功")
                
        # 进程退出处理
        if not process_running and self.state['modified']:
            if self._restore_config():
                self.logger.info("配置恢复成功")

    def _save_lesson_state(self):
        """安全保存课程相关状态（修复版）"""
        try:
            # 创建要保存的状态数据
            state_to_save = {
                'modified': self.state['modified'],
                'backup_done': self.state['backup_done'],
                'lesson_modified': self.state['lesson_modified'],
                'lesson_backup_done': self.state['lesson_backup_done']
            }

            # 使用原子写入方式防止文件损坏
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state_to_save, f, indent=4)

            # 替换原文件
            temp_file.replace(self.state_file)
            
            # 单独保存课程备份（使用相同安全方式）
            if self.state['lesson_original_value']:
                lesson_backup = self.config_dir / "lesson_backup.json"
                temp_backup = lesson_backup.with_suffix('.tmp')
                with open(temp_backup, 'w') as f:
                    json.dump({'widgets': self.state['lesson_original_value']}, f, indent=4)
                temp_backup.replace(lesson_backup)
            
        except Exception as e:
            self.logger.error(f"课程状态保存失败: {str(e)}")
            # 清理可能残留的临时文件
            for f in [temp_file, temp_backup]:
                if f and f.exists():
                    try:
                        f.unlink()
                    except:
                        pass

    def _check_lesson_change(self):
        """检测课程变化"""
        current_lesson = self.cw_contexts.get('Current_Lesson', '')
        
        # 首次检测或发生变化时记录时间戳
        if current_lesson != self.state['current_lesson']:
            self.state['current_lesson'] = current_lesson
            self.state['last_lesson_change'] = time.time()
            self.logger.debug(f"课程变化检测: {current_lesson}")
            
        return current_lesson

    def _lesson_condition_met(self):
        """检查课程触发条件"""
        current_lesson = self.state['current_lesson']
        return current_lesson in LESSON_TRIGGERS

    def _create_lesson_backup(self, widgets):
        """创建课程相关备份"""
        if self.state['lesson_backup_done']:
            return True
            
        try:
            original_widgets = widgets.copy()
            self.state['lesson_original_value'] = original_widgets
            self.state['lesson_backup_done'] = True
            self._save_lesson_state()
            self.logger.info("课程相关配置备份成功")
            return True
        except Exception as e:
            self.logger.error(f"课程备份失败: {str(e)}")
            return False

    def _modify_for_lesson(self):
        """执行课程相关修改"""
        try:
            with open(self.target_config, 'r+') as f:
                data = json.load(f)
                widgets = data.get('widgets', [])
                
                # 验证修改条件
                target_index = self._find_widget_index(widgets, WIDGET_TARGET_PAIR[0])
                if target_index == -1:
                    self.logger.warning("目标组件不存在，跳过修改")
                    return False
                if WIDGET_TARGET_PAIR[1] in widgets:
                    self.logger.warning("目标组件已存在，跳过修改")
                    return False
                
                # 创建备份
                if not self._create_lesson_backup(widgets):
                    return False
                
                # 执行修改
                widgets[target_index] = WIDGET_TARGET_PAIR[1]
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
                
                self.state['lesson_modified'] = True
                self._save_lesson_state()
                self.logger.info(f"课程触发修改成功: {WIDGET_TARGET_PAIR[0]} → {WIDGET_TARGET_PAIR[1]}")
                return True
        except Exception as e:
            self.logger.error(f"课程相关修改失败: {str(e)}")
            return False

    def _restore_for_lesson(self):
        """恢复课程相关配置"""
        if not self.state['lesson_backup_done']:
            return False
            
        try:
            original_widgets = self.state['lesson_original_value']
            with open(self.target_config, 'r+') as f:
                data = json.load(f)
                current_widgets = data.get('widgets', [])
                
                # 只恢复被修改的部分
                try:
                    target_index = current_widgets.index(WIDGET_TARGET_PAIR[1])
                    current_widgets[target_index] = WIDGET_TARGET_PAIR[0]
                except ValueError:
                    self.logger.warning("目标组件不存在，无需恢复")
                    return True
                
                # 写入修改
                data['widgets'] = current_widgets
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
                
                self.state.update({
                    'lesson_modified': False,
                    'lesson_backup_done': False,
                    'lesson_original_value': None
                })
                self._save_lesson_state()
                
                # 清理备份文件
                (self.config_dir / "lesson_backup.json").unlink(missing_ok=True)
                self.logger.info("课程相关配置恢复成功")
                return True
        except Exception as e:
            self.logger.error(f"课程恢复失败: {str(e)}")
            return False

    def _find_widget_index(self, widgets, target):
        """查找组件索引"""
        try:
            return widgets.index(target)
        except ValueError:
            return -1
        
    def _reset_state(self):
        """重置为初始状态"""
        backup_files = [
            self.state_file,
            self.original_file,
            self.config_dir / "lesson_backup.json"
        ]
        
        for f in backup_files:
            try:
                if f.exists():
                    f.unlink()
            except Exception as e:
                self.logger.error(f"清理文件失败 {f.name}: {str(e)}")
        
        self.state.update({
            'modified': False,
            'backup_done': False,
            'lesson_modified': False,
            'lesson_backup_done': False,
            'lesson_original_value': None
        })
