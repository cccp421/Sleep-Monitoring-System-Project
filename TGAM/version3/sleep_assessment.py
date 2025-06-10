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

        # 健康监测指标区 - 使用网格布局，2列4行
        health_metrics_label = QLabel("<b>健康监测指标</b>")
        health_metrics_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        health_metrics_label.setStyleSheet("padding: 15px 0 8px 0; color: #2E86C1;")
        layout.addWidget(health_metrics_label)

        # 健康监测网格布局 - 增加列宽
        self.health_grid = QGridLayout()
        self.health_grid.setHorizontalSpacing(30)  # 增加列间距
        self.health_grid.setVerticalSpacing(12)

        # 初始化健康监测指标标签 - 每行3部分：名称、值+单位、范围
        health_items = [
            ("heart_rate", "心率:", "-", "次/分"),
            ("blood_oxygen", "血氧:", "-", "%"),
            ("temperature", "体温:", "-", "℃"),
            ("respiration_rate", "呼吸频率:", "-", "次/分"),
            ("ambient_temp", "环境温度:", "-", "℃"),
            ("systolic_bp", "收缩压:", "-", "mmHg"),
            ("diastolic_bp", "舒张压:", "-", "mmHg"),
            ("fatigue", "疲劳指数:", "-", "")
        ]

        self.health_labels = {}
        for i, (key, label, value, unit) in enumerate(health_items):
            row = i // 2  # 每2列，所以行数为0-3
            col = (i % 2) * 3  # 每列占3列：名称、值、范围

            # 名称标签
            name_label = QLabel(label)
            name_label.setFont(QFont("Microsoft YaHei", 9))
            name_label.setFixedWidth(70)  # 固定宽度确保对齐
            name_label.setStyleSheet("font-weight: bold;")
            self.health_grid.addWidget(name_label, row, col)

            # 值标签（包含单位）
            value_str = f"{value} {unit}"
            value_label = QLabel(value_str)
            value_label.setFont(QFont("Microsoft YaHei", 9))
            value_label.setFixedWidth(80)  # 固定宽度
            value_label.setAlignment(Qt.AlignLeft)
            self.health_grid.addWidget(value_label, row, col + 1)

            # 范围标签
            min_val, max_val, _ = self.health_ranges.get(key, (0, 0, ""))
            range_text = f"[正常范围: {min_val}-{max_val}]"
            range_label = QLabel(range_text)
            range_label.setFont(QFont("Microsoft YaHei", 8))
            range_label.setStyleSheet("color: #7F8C8D; font-style: italic;")
            self.health_grid.addWidget(range_label, row, col + 2)

            self.health_labels[f"{key}_value"] = value_label

        layout.addLayout(self.health_grid)

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
        file_btn.setStyleSheet("padding: 6px 12px; border-radius: 4px;")
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
        self.process_data()

    def eeg_data_selected(self, file_path):
        """处理选择的脑电检测数据文件"""
        self.eeg_data_path = file_path
        self.status_label.setText(f"已选择脑电检测文件: {os.path.basename(file_path)}")
        self.process_data()

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

    def process_data(self):
        """处理并显示健康检测和脑电检测数据"""
        if not self.health_data_path or not self.eeg_data_path:
            # 如果没有选择两个文件，不进行处理
            if not self.health_data_path and not self.eeg_data_path:
                self.status_label.setText("请选择健康检测和脑电检测数据文件")
            elif not self.health_data_path:
                self.status_label.setText("请选择健康检测数据文件")
            else:
                self.status_label.setText("请选择脑电检测数据文件")
            return

        try:
            # 模拟数据处理 - 在实际应用中应替换为实际的数据加载和处理逻辑
            self.status_label.setText("正在处理数据...")

            # 1. 处理健康监测数据
            try:
                health_df = pd.read_csv(self.health_data_path)

                # 添加健康监测数据摘要信息
                health_file = os.path.basename(self.health_data_path)
                _, health_date, health_time = health_file.split('_')

                # 解析日期和时间
                date_str = health_date  # "20250610"
                date_display = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                health_time = health_time.split('.')[0]  # "173102"
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
                # 收缩压：正常范围 60-200
                health_df = self.filter_abnormal_data(health_df, 'SystolicBP', 60, 200)
                # 舒张压：正常范围 40-120
                health_df = self.filter_abnormal_data(health_df, 'DiastolicBP', 40, 120)
                # 疲劳指数：正常范围 0-100
                health_df = self.filter_abnormal_data(health_df, 'Fatigue', 0, 100)

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

            except Exception as e:
                self.status_label.setText(f"健康数据处理错误: {str(e)}")
                import traceback
                traceback.print_exc()
                return

            # 2. 生成睡眠评估指标 (这里仍然是模拟数据)
            # 从文件名解析时间和用户信息
            eeg_file = os.path.basename(self.eeg_data_path)
            _, eeg_date, eeg_time = eeg_file.split('_')

            # 用户信息 - 在实际应用中应从文件中提取
            user_info = "用户ID: 001 | 性别: 男 | 年龄: 32"

            # 模拟数据读取和处理结果
            self.report_data = {
                # 睡眠指标
                "sleep_duration": "7.2小时",
                "deep_sleep": "28% (良好)",
                "light_sleep": "52% (正常)",
                "rem_sleep": "20% (正常)",
                "sleep_latency": "18分钟 (良好)",
                "awakenings": "3次 (正常)",
                "sleep_efficiency": "92% (优秀)",
                "sleep_score": "86/100 (良好)",

                # 数据摘要
                "user_info": user_info,
                "detection_time": f"{date_display} {health_time_display}",
                "records_count": f"{len(health_df)}条健康记录"
            }

            # 更新界面显示
            self.update_data_display()
            self.status_label.setText(f"数据分析完成: {date_display} 数据已处理")

        except Exception as e:
            self.status_label.setText(f"数据处理错误: {str(e)}")
            import traceback
            traceback.print_exc()

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