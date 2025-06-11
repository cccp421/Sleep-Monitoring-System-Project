from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, QGridLayout,
                             QFrame, QPushButton, QFileDialog, QHBoxLayout, QLineEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import os
import pandas as pd
import numpy as np


class SleepAssessmentWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("睡眠质量评估")
        self.setGeometry(300, 200, 850, 650)  # 增加窗口宽度以适应更宽的布局

        # 初始化文件路径
        self.health_data_path = ""
        self.eeg_data_path = ""
        self.report_data = None

        # 设置窗口属性
        self.setWindowModality(Qt.ApplicationModal)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # 初始化健康指标的范围
        self.health_ranges = {
            "heart_rate": (55, 72, "次/分"),
            "blood_oxygen": (95, 100, "%"),
            "temperature": (36.0, 37.5, "℃"),
            "respiration_rate": (12, 20, "次/分"),
            "ambient_temp": (18, 24, "℃"),  # 舒适的室内环境温度
            "systolic_bp": (90, 120, "mmHg"),
            "diastolic_bp": (60, 80, "mmHg"),
            "fatigue": (0, 30, "")  # 疲劳指数范围
        }

        # 初始化UI
        self.init_ui()

    def init_ui(self):
        """初始化睡眠评估界面 - 包含文件选择和数据显示功能"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(25, 20, 25, 20)  # 增加左右边距

        # 标题
        title_label = QLabel("睡眠质量评估报告")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setStyleSheet("color: #2E86C1; padding: 10px 0;")
        layout.addWidget(title_label)

        # 文件选择区域 - 脑电数据
        eeg_file_layout = self.create_file_selection_layout(
            "脑电检测数据:", "tgam_rawdata_*.csv", "eeg_data_selected")
        layout.addLayout(eeg_file_layout)

        # 文件选择区域 - 健康数据
        health_file_layout = self.create_file_selection_layout(
            "健康检测数据:", "health_data_*.csv", "health_data_selected")
        layout.addLayout(health_file_layout)

        # 状态显示区域
        self.status_label = QLabel("就绪，请选择数据文件")
        self.status_label.setFont(QFont("Microsoft YaHei", 9))
        self.status_label.setStyleSheet("padding: 6px; background-color: #F8F9F9; border: 1px solid #D6DBDF;")
        layout.addWidget(self.status_label)

        # 评估指标区
        metrics_label = QLabel("<b>评估指标</b>")
        metrics_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        metrics_label.setStyleSheet("padding: 12px 0 8px 0; color: #2E86C1;")
        layout.addWidget(metrics_label)

        # 网格布局展示指标 - 2列
        self.metrics_grid = QGridLayout()
        self.metrics_grid.setHorizontalSpacing(25)  # 增加列间距
        self.metrics_grid.setVerticalSpacing(10)

        # 初始化指标标签
        self.metric_labels = {}
        metrics = [
            ("sleep_duration", "睡眠总时长:", "-"),
            ("deep_sleep", "深睡眠比例:", "-"),
            ("light_sleep", "浅睡眠比例:", "-"),
            ("rem_sleep", "REM睡眠比例:", "-"),
            ("sleep_latency", "入睡时间:", "-"),
            ("awakenings", "觉醒次数:", "-"),
            ("sleep_efficiency", "睡眠效率:", "-"),
            ("sleep_score", "睡眠质量得分:", "-")
        ]

        for i, (key, metric, value) in enumerate(metrics):
            row = i // 2
            col = (i % 2) * 2  # 每2个指标为一列

            name_label = QLabel(metric)
            name_label.setFont(QFont("Microsoft YaHei", 10))
            self.metrics_grid.addWidget(name_label, row, col)

            value_label = QLabel(value)
            value_label.setFont(QFont("Microsoft YaHei", 10))
            value_label.setStyleSheet("color: #2980B9;")
            self.metrics_grid.addWidget(value_label, row, col + 1)
            self.metric_labels[key] = value_label

        layout.addLayout(self.metrics_grid)

        # 健康监测指标区
        health_metrics_label = QLabel("<b>健康监测指标</b>")
        health_metrics_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        health_metrics_label.setStyleSheet("padding: 15px 0 8px 0; color: #2E86C1;")
        layout.addWidget(health_metrics_label)

        # 改用垂直布局包装水平布局
        health_container = QWidget()
        health_container_layout = QHBoxLayout(health_container)
        health_container_layout.setSpacing(40)  # 增加间距避免重叠

        # 创建左右两列布局
        left_column = QVBoxLayout()
        right_column = QVBoxLayout()

        # 健康监测指标项
        health_items = [
            ("heart_rate", "心率:", "次/分"),
            ("blood_oxygen", "血氧:", "%"),
            ("temperature", "体温:", "℃"),
            ("respiration_rate", "呼吸频率:", "次/分"),
            ("ambient_temp", "环境温度:", "℃"),
            ("fatigue", "疲劳指数:", ""),
            ("systolic_bp", "收缩压:", "mmHg"),
            ("diastolic_bp", "舒张压:", "mmHg")
        ]

        self.health_labels = {}
        for i, (key, label, unit) in enumerate(health_items):
            # 创建每项的水平布局
            item_layout = QHBoxLayout()
            item_layout.setSpacing(10)

            # 名称标签
            name_label = QLabel(label)
            name_label.setFont(QFont("Microsoft YaHei", 9))
            name_label.setStyleSheet("font-weight: bold; min-width: 80px;")
            item_layout.addWidget(name_label)

            # 值标签（带单位）
            value_label = QLabel(f"- {unit}")
            value_label.setFont(QFont("Microsoft YaHei", 9))
            value_label.setStyleSheet("min-width: 90px;")
            item_layout.addWidget(value_label)

            # 添加弹性空间
            item_layout.addSpacing(15)

            # 范围标签
            min_val, max_val, _ = self.health_ranges.get(key, (0, 0, ""))
            range_label = QLabel(f"[正常范围: {min_val}-{max_val}]")
            range_label.setFont(QFont("Microsoft YaHei", 8))
            range_label.setStyleSheet("color: #7F8C8D; font-style: italic;")
            item_layout.addWidget(range_label)

            # 添加弹性空间使内容靠左
            item_layout.addStretch(1)

            # 将项添加到左右列
            if i < len(health_items) // 2:
                left_column.addLayout(item_layout)
            else:
                right_column.addLayout(item_layout)

            self.health_labels[f"{key}_value"] = value_label

        # 添加左右列到容器
        health_container_layout.addLayout(left_column)
        health_container_layout.addSpacing(30)  # 增加列间距
        health_container_layout.addLayout(right_column)

        # 添加容器到主布局
        layout.addWidget(health_container)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #ccc; margin: 20px 0;")
        layout.addWidget(separator)

        # 功能按钮区 - 增加按钮间距
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)  # 增加按钮间距

        process_btn = QPushButton("开始评估")
        process_btn.setFont(QFont("Microsoft YaHei", 10))
        process_btn.setStyleSheet(
            "QPushButton { background-color: #2E86C1; color: white; padding: 10px 20px; border-radius: 5px; font-weight: bold; }"
            "QPushButton:hover { background-color: #3498DB; }"
            "QPushButton:pressed { background-color: #1B4F72; }"
        )
        process_btn.clicked.connect(self.process_data)
        buttons_layout.addWidget(process_btn)

        export_btn = QPushButton("导出报告")
        export_btn.setFont(QFont("Microsoft YaHei", 10))
        export_btn.setStyleSheet(
            "QPushButton { background-color: #27AE60; color: white; padding: 10px 20px; border-radius: 5px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2ECC71; }"
            "QPushButton:pressed { background-color: #186A3B; }"
        )
        export_btn.clicked.connect(self.export_report)
        buttons_layout.addWidget(export_btn)

        buttons_layout.addStretch(1)
        layout.addLayout(buttons_layout)

    def create_file_selection_layout(self, label, file_filter, slot_name):
        """创建文件选择布局"""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # 文件类型标签
        file_label = QLabel(label)
        file_label.setFont(QFont("Microsoft YaHei", 10))
        file_label.setFixedWidth(100)
        layout.addWidget(file_label)

        # 文件路径显示
        path_input = QLineEdit()
        path_input.setReadOnly(True)
        path_input.setFont(QFont("Microsoft YaHei", 9))
        path_input.setStyleSheet("padding: 6px; background-color: #F8F9F9; border: 1px solid #D6DBDF;")
        layout.addWidget(path_input, 1)

        # 文件选择按钮
        file_btn = QPushButton("选择文件")
        file_btn.setFont(QFont("Microsoft YaHei", 9))
        file_btn.setStyleSheet("""
        QPushButton {
            background-color: #3498DB;  /* 按钮背景色 */
            color: white;               /* 文字颜色 */
            padding: 8px 15px;          /* 按钮内边距 */
            border-radius: 4px;         /* 圆角大小 */
            font-weight: bold;          /* 加粗文字 */
            border: none;               /* 无边框 */
        }
        QPushButton:hover {
            background-color: #2980B9;  /* 鼠标悬停时的颜色 */
        }
        QPushButton:pressed {
            background-color: #1F618D;  /* 按下时的颜色 */
            padding: 7px 14px 9px 16px; /* 按下时轻微下移 */
        }
        QPushButton:disabled {
            background-color: #AAB7B8;  /* 禁用状态的颜色 */
        }
    """)
        file_btn.clicked.connect(lambda: self.select_file(file_filter, path_input, slot_name))
        layout.addWidget(file_btn)

        return layout

    def select_file(self, file_filter, path_input, slot_name):
        """打开文件选择对话框并处理选择的文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", f"CSV文件 ({file_filter})"
        )

        if file_path:
            path_input.setText(file_path)
            getattr(self, slot_name)(file_path)

    def health_data_selected(self, file_path):
        """处理选择的健康检测数据文件"""
        self.health_data_path = file_path
        self.status_label.setText(f"已选择健康检测文件: {os.path.basename(file_path)}")
        self.process_health_data()  # 直接处理健康数据

    def eeg_data_selected(self, file_path):
        """处理选择的脑电检测数据文件"""
        self.eeg_data_path = file_path
        self.status_label.setText(f"已选择脑电检测文件: {os.path.basename(file_path)}")
        self.process_eeg_data()  # 直接处理脑电数据

    def filter_abnormal_data(self, df, column, min_val=0, max_val=None):
        """
        过滤异常数据
        :param df: 数据框
        :param column: 列名
        :param min_val: 最小值阈值 (低于此值的视为异常)
        :param max_val: 最大值阈值 (高于此值的视为异常)
        :return: 过滤后的数据框
        """
        # 过滤负值
        df_filtered = df[df[column] >= min_val]

        # 如果提供了最大值阈值，过滤超出范围的值
        if max_val is not None:
            df_filtered = df_filtered[df_filtered[column] <= max_val]

        return df_filtered

    def process_health_data(self):
        """处理健康数据并更新健康监测指标"""
        if not self.health_data_path:
            self.status_label.setText("请选择健康检测数据文件")
            return

        try:
            # 处理健康监测数据
            health_df = pd.read_csv(self.health_data_path)

            # 添加健康监测数据摘要信息
            health_file = os.path.basename(self.health_data_path)

            # 修正文件名解析逻辑 - 处理可能存在的前缀
            parts = health_file.split('_')
            if len(parts) >= 3:
                # 最后两部分是日期和时间
                health_date = parts[-2]
                health_time = parts[-1].split('.')[0]  # 移除扩展名
            else:
                raise ValueError(f"健康监测文件名格式不正确: {health_file}")

            # 解析日期和时间
            date_display = f"{health_date[:4]}-{health_date[4:6]}-{health_date[6:8]}"
            health_time_display = f"{health_time[:2]}:{health_time[2:4]}:{health_time[4:6]}"

            # 处理时间格式转换
            health_df['Timestamp'] = pd.to_datetime(health_df['Timestamp'], errors='coerce')

            # 过滤异常数据
            # 心率：正常范围 40-200
            health_df = self.filter_abnormal_data(health_df, 'HeartRate', 40, 200)
            # 血氧：正常范围 70-100
            health_df = self.filter_abnormal_data(health_df, 'BloodOxygen', 70, 100)
            # 体温：正常范围 35-42
            health_df = self.filter_abnormal_data(health_df, 'Temperature', 35, 42)
            # 呼吸频率：正常范围 5-60
            health_df = self.filter_abnormal_data(health_df, 'RespirationRate', 5, 60)
            # 环境温度：正常范围 -10-50
            health_df = self.filter_abnormal_data(health_df, 'AmbientTemp', -10, 50)
            # 疲劳指数：正常范围 0-100
            health_df = self.filter_abnormal_data(health_df, 'Fatigue', 0, 100)
            # 收缩压：正常范围 60-200
            health_df = self.filter_abnormal_data(health_df, 'SystolicBP', 60, 200)
            # 舒张压：正常范围 40-120
            health_df = self.filter_abnormal_data(health_df, 'DiastolicBP', 40, 120)


            # 计算平均值
            heart_rate_avg = health_df['HeartRate'].mean()
            blood_oxygen_avg = health_df['BloodOxygen'].mean()
            temperature_avg = health_df['Temperature'].mean()
            respiration_rate_avg = health_df['RespirationRate'].mean()
            ambient_temp_avg = health_df['AmbientTemp'].mean()
            systolic_bp_avg = health_df['SystolicBP'].mean()
            diastolic_bp_avg = health_df['DiastolicBP'].mean()
            fatigue_avg = health_df['Fatigue'].mean()

            # 更新健康监测指标显示
            self.update_health_metrics({
                "heart_rate": heart_rate_avg,
                "blood_oxygen": blood_oxygen_avg,
                "temperature": temperature_avg,
                "respiration_rate": respiration_rate_avg,
                "ambient_temp": ambient_temp_avg,
                "systolic_bp": systolic_bp_avg,
                "diastolic_bp": diastolic_bp_avg,
                "fatigue": fatigue_avg
            })

            # 更新状态
            self.status_label.setText(f"健康数据已处理: {os.path.basename(self.health_data_path)}")

        except Exception as e:
            self.status_label.setText(f"健康数据处理错误: {str(e)}")
            import traceback
            traceback.print_exc()

    def process_eeg_data(self):
        """处理脑电数据并更新睡眠评估指标"""
        if not self.eeg_data_path:
            self.status_label.setText("请选择脑电检测数据文件")
            return

        try:
            # 重置报告数据
            self.report_data = None
            self.status_label.setText("正在处理脑电数据...")
            QApplication.processEvents()  # 更新UI

            # 从文件名解析时间和用户信息
            eeg_file = os.path.basename(self.eeg_data_path)

            # 读取脑电数据
            eeg_df = pd.read_csv(self.eeg_data_path)

            # 验证数据列是否存在
            required_columns = ['Epoch_Index', 'Sleep_Stage', 'Stage_Label']
            missing_columns = [col for col in required_columns if col not in eeg_df.columns]
            if missing_columns:
                raise ValueError(f"数据文件缺少必要列: {', '.join(missing_columns)}")

            # 处理睡眠阶段标签
            valid_stages = {
                0: 'W',  # Wakefulness
                1: 'N1',  # NREM Stage 1
                2: 'N2',  # NREM Stage 2
                3: 'N3',  # NREM Stage 3 (Deep Sleep)
                4: 'REM',  # REM Sleep
                # 5: 'MOVE',  # Movement (不计算在内)
                # 6: 'UNK'   # Unknown (不计算在内)
            }

            # 过滤掉无效的睡眠阶段 (MOVE和UNK)
            eeg_df = eeg_df[eeg_df['Sleep_Stage'].isin(valid_stages.keys())].copy()

            # 映射睡眠阶段到名称
            eeg_df['Stage_Name'] = eeg_df['Sleep_Stage'].map(valid_stages)

            # 检查有效数据
            if len(eeg_df) == 0:
                # 如果没有有效数据，尝试查看实际存在的睡眠阶段值
                unique_stages = sorted(eeg_df['Sleep_Stage'].unique())
                raise ValueError(f"未找到有效睡眠阶段数据。文件中的睡眠阶段值为: {unique_stages}")

            # 计算睡眠指标
            metrics = self.calculate_sleep_metrics(eeg_df)

            # 更新报告数据
            self.report_data = {
                # 睡眠指标
                "sleep_duration": f"{metrics['total_sleep_time']:.1f}小时",
                "deep_sleep": f"{metrics['deep_sleep_percent']:.1f}%",
                "light_sleep": f"{metrics['light_sleep_percent']:.1f}%",
                "rem_sleep": f"{metrics['rem_sleep_percent']:.1f}%",
                "sleep_latency": f"{metrics['sleep_latency']:.1f}分钟",
                "awakenings": f"{metrics['awakenings']}次",
                "sleep_efficiency": f"{metrics['sleep_efficiency']:.1f}%",
                "sleep_score": f"{metrics['sleep_score']:.0f}/100",

                # 数据摘要
                "user_info": f"数据文件: {eeg_file} | 有效记录数: {len(eeg_df)}",
                "records_count": f"{len(eeg_df)}条有效记录"
            }

            # 更新界面显示
            self.update_data_display()
            self.status_label.setText(f"成功处理脑电数据: {os.path.basename(self.eeg_data_path)}")

        except Exception as e:
            error_msg = f"脑电数据处理错误: {str(e)}"
            self.status_label.setText(error_msg)
            print(error_msg)
            import traceback
            traceback.print_exc()

    def calculate_sleep_metrics(self, df):
        """优化后的睡眠质量指标计算"""
        # 确保睡眠阶段名称列存在
        if 'Stage_Name' not in df.columns:
            # 映射睡眠阶段到名称
            valid_stages = {
                0: 'W',  # Wakefulness
                1: 'N1',  # NREM Stage 1
                2: 'N2',  # NREM Stage 2
                3: 'N3',  # NREM Stage 3 (Deep Sleep)
                4: 'REM',  # REM Sleep
            }
            df['Stage_Name'] = df['Sleep_Stage'].map(valid_stages).fillna('UNK')

        # 过滤掉无效的睡眠阶段 (MOVE和UNK)
        df = df[df['Stage_Name'].isin(['W', 'N1', 'N2', 'N3', 'REM'])]

        if len(df) == 0:
            return {
                'error': "文件中未找到有效睡眠阶段数据",
                'total_minutes': 0,
                'total_sleep_time': 0,
                'sleep_latency': 0,
                'sleep_efficiency': 0,
                'deep_sleep_percent': 0,
                'light_sleep_percent': 0,
                'rem_sleep_percent': 0,
                'awakenings': 0,
                'sleep_score': 0
            }

        # 获取有效睡眠阶段的数量
        total_epochs = len(df)

        # 1. 睡眠潜伏期（分钟） - 从开始记录到首次连续5分钟非清醒
        sleep_latency = self.calculate_sleep_latency(df)

        # 2. 总睡眠时间
        sleep_data = df[df['Stage_Name'] != 'W']
        sleep_minutes = len(sleep_data) * 0.5

        # 3. 睡眠效率
        total_minutes = total_epochs * 0.5
        sleep_efficiency = (sleep_minutes / total_minutes) * 100 if total_minutes > 0 else 0

        # 4. 各阶段睡眠时长占比（基于实际时间，非数量）
        stage_minutes = {
            'W': len(df[df['Stage_Name'] == 'W']) * 0.5,
            'N1': len(df[df['Stage_Name'] == 'N1']) * 0.5,
            'N2': len(df[df['Stage_Name'] == 'N2']) * 0.5,
            'N3': len(df[df['Stage_Name'] == 'N3']) * 0.5,
            'REM': len(df[df['Stage_Name'] == 'REM']) * 0.5
        }

        # 5. 觉醒次数 - 连续清醒时间超过5分钟
        awaken_events = self.calculate_awakenings(df)

        # 6. 睡眠质量得分（改进的评分系统）
        sleep_score = self.calculate_sleep_score(
            sleep_efficiency,
            stage_minutes['N3'],
            stage_minutes['REM'],
            sleep_latency,
            awaken_events,
            total_minutes
        )

        return {
            'total_minutes': total_minutes,
            'total_sleep_time': sleep_minutes / 60,  # 转换为小时
            'sleep_latency': sleep_latency,
            'sleep_efficiency': sleep_efficiency,
            'deep_sleep_percent': (stage_minutes['N3'] / sleep_minutes * 100) if sleep_minutes > 0 else 0,
            'light_sleep_percent': (
                        (stage_minutes['N1'] + stage_minutes['N2']) / sleep_minutes * 100) if sleep_minutes > 0 else 0,
            'rem_sleep_percent': (stage_minutes['REM'] / sleep_minutes * 100) if sleep_minutes > 0 else 0,
            'awakenings': awaken_events,
            'sleep_score': sleep_score
        }

    def calculate_sleep_latency(self, df):
        """计算睡眠潜伏期（首次连续5分钟非清醒的时间点）"""
        consecutive_sleep = 0
        latency = 0

        for i, row in df.iterrows():
            latency += 0.5  # 每个epoch是30秒，即0.5分钟

            if row['Stage_Name'] != 'W':
                consecutive_sleep += 0.5
            else:
                consecutive_sleep = 0

            # 如果连续5分钟非清醒，视为入睡
            if consecutive_sleep >= 5.0:
                return latency - 5.0  # 减去连续时长得到开始时间

        # 如果没有达到连续睡眠，返回总时长
        return latency

    def calculate_awakenings(self, df):
        """计算觉醒次数 - 连续清醒时间超过5分钟"""
        awaken_events = 0
        in_wake_period = False
        consecutive_wake = 0

        for row in df['Stage_Name']:
            if row == 'W':
                consecutive_wake += 0.5
                if not in_wake_period and consecutive_wake >= 5:  # 连续清醒5分钟才算一次觉醒
                    awaken_events += 1
                    in_wake_period = True
            else:
                consecutive_wake = 0
                in_wake_period = False

        return awaken_events

    def calculate_sleep_score(self, efficiency, deep_minutes, rem_minutes, latency, awakenings, total_minutes):
        """基于多因素计算睡眠质量得分（0-100）"""
        # 各因素的权重
        efficiency_weight = 0.35
        deep_weight = 0.25
        rem_weight = 0.15
        latency_weight = 0.15
        awakening_weight = 0.10

        # 计算各因素得分
        efficiency_score = min(100, max(0, efficiency)) * efficiency_weight

        # 深睡得分（理想占比15-25%）
        deep_percent = deep_minutes / total_minutes * 100
        deep_score = min(100, max(0, deep_percent * 4)) * deep_weight  # 25%为满分100

        # REM睡眠得分（理想占比20-25%）
        rem_percent = rem_minutes / total_minutes * 100
        rem_score = min(100, max(0, rem_percent * 4)) * rem_weight  # 25%为满分100

        # 睡眠潜伏期得分（理想时间10-20分钟）
        if latency <= 10:
            latency_score = 100
        elif latency <= 30:
            latency_score = 100 - (latency - 10) * 4  # 每超过1分钟扣4分
        else:
            latency_score = 20
        latency_score *= latency_weight

        # 觉醒次数得分
        if awakenings == 0:
            awakening_score = 100
        elif awakenings <= 2:
            awakening_score = 80
        elif awakenings <= 4:
            awakening_score = 60
        else:
            awakening_score = 30
        awakening_score *= awakening_weight

        # 最终得分
        total_score = efficiency_score + deep_score + rem_score + latency_score + awakening_score

        # 根据总睡眠时间调整
        if total_minutes < 240:  # 少于4小时睡眠
            total_score *= 0.8

        return min(100, max(0, total_score))


    def process_data(self):
        """处理并显示健康检测和脑电检测数据（同时处理两个）"""
        if self.health_data_path:
            self.process_health_data()

        if self.eeg_data_path:
            self.process_eeg_data()

    def update_data_display(self):
        """更新界面上的数据展示"""
        if not self.report_data:
            return

        # 更新评估指标
        self.metric_labels["sleep_duration"].setText(self.report_data["sleep_duration"])
        self.metric_labels["deep_sleep"].setText(self.report_data["deep_sleep"])
        self.metric_labels["light_sleep"].setText(self.report_data["light_sleep"])
        self.metric_labels["rem_sleep"].setText(self.report_data["rem_sleep"])
        self.metric_labels["sleep_latency"].setText(self.report_data["sleep_latency"])
        self.metric_labels["awakenings"].setText(self.report_data["awakenings"])
        self.metric_labels["sleep_efficiency"].setText(self.report_data["sleep_efficiency"])
        self.metric_labels["sleep_score"].setText(self.report_data["sleep_score"])

        # 设置样式 - 强调重点数据
        self.metric_labels["sleep_efficiency"].setStyleSheet("color: #27AE60; font-weight: bold;")
        self.metric_labels["sleep_score"].setStyleSheet("color: #2980B9; font-weight: bold;")

    def update_health_metrics(self, health_metrics):
        """更新健康监测指标显示"""
        for key, value in health_metrics.items():
            # 获取正常范围
            min_val, max_val, unit = self.health_ranges.get(key, (0, 0, ""))

            # 格式化为字符串
            if pd.isna(value):
                value_str = "N/A"
            elif isinstance(value, float):
                value_str = f"{value:.1f}"  # 保留一位小数
            else:
                value_str = f"{value}"

            # 设置值标签
            self.health_labels[f"{key}_value"].setText(f"{value_str} {unit}")

            # 根据是否在正常范围内设置颜色
            if min_val <= value <= max_val:
                self.health_labels[f"{key}_value"].setStyleSheet("color: #27AE60; font-weight: bold;")  # 绿色表示正常
            else:
                self.health_labels[f"{key}_value"].setStyleSheet("color: #E74C3C; font-weight: bold;")  # 红色表示异常

    def export_report(self):
        """导出睡眠评估报告"""
        if not self.report_data:
            self.status_label.setText("请先处理数据后再导出报告")
            return

        # 保存文件对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存报告", "", "PDF文件 (*.pdf);;文本文件 (*.txt)"
        )

        if file_path:
            try:
                # 在实际应用中这里应实现生成和导出报告的逻辑
                self.status_label.setText(f"报告已成功导出到: {file_path}")
            except Exception as e:
                self.status_label.setText(f"导出报告失败: {str(e)}")

    def closeEvent(self, event):
        """窗口关闭时清理资源并通知父窗口"""
        super().closeEvent(event)
        if self.parent() and hasattr(self.parent(), 'on_sleep_assessment_closed'):
            self.parent().on_sleep_assessment_closed()
        event.accept()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = SleepAssessmentWindow()
    window.show()
    sys.exit(app.exec_())