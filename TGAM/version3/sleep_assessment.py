from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, QGridLayout,
                             QFrame, QPushButton, QFileDialog, QHBoxLayout, QLineEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import os
import pandas as pd
from PyQt5.QtWidgets import QApplication
from assessment_result import AssessmentResultWindow  # 导入评估结果窗口
from pdf_report_generator import PDFReportGenerator
from datetime import datetime

class SleepAssessmentWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("睡眠质量评估")
        self.setGeometry(300, 200, 850, 650)

        # Initialize file paths and data
        self.health_data_path = ""
        self.eeg_data_path = ""
        self.report_data = None
        self.health_metrics = None  # Added to store health metrics

        # Set window properties
        self.setWindowModality(Qt.ApplicationModal)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Health metrics ranges
        self.health_ranges = {
            "heart_rate": (55, 72, "次/分"),
            "blood_oxygen": (95, 100, "%"),
            "temperature": (36.0, 37.5, "℃"),
            "respiration_rate": (12, 20, "次/分"),
            "ambient_temp": (18, 24, "℃"),
            "systolic_bp": (90, 120, "mmHg"),
            "diastolic_bp": (60, 80, "mmHg"),
            "fatigue": (0, 30, "")
        }

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(25, 20, 25, 20)

        title_label = QLabel("睡眠质量评估报告")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setStyleSheet("color: #2E86C1; padding: 10px 0;")
        layout.addWidget(title_label)

        eeg_file_layout = self.create_file_selection_layout(
            "脑电检测数据:", "tgam_rawdata_*.csv", "eeg_data_selected")
        layout.addLayout(eeg_file_layout)

        health_file_layout = self.create_file_selection_layout(
            "健康检测数据:", "health_data_*.csv", "health_data_selected")
        layout.addLayout(health_file_layout)

        # 使用 QLineEdit 替代 QLabel，实现可滚动显示
        self.status_edit = QLineEdit("就绪，请选择数据文件")
        self.status_edit.setReadOnly(True)  # 设置为只读
        self.status_edit.setFont(QFont("Microsoft YaHei", 9))
        self.status_edit.setStyleSheet("""
            padding: 6px;
            background-color: #F8F9F9;
            border: 1px solid #D6DBDF;
            qproperty-frame: false;
        """)
        self.status_edit.setFixedWidth(800)  # 设置固定宽度
        self.status_edit.setFixedHeight(30)   # 设置固定高度
        layout.addWidget(self.status_edit)

        metrics_label = QLabel("<b>评估指标</b>")
        metrics_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        metrics_label.setStyleSheet("padding: 12px 0 8px 0; color: #2E86C1;")
        layout.addWidget(metrics_label)

        self.metrics_grid = QGridLayout()
        self.metrics_grid.setHorizontalSpacing(25)
        self.metrics_grid.setVerticalSpacing(10)

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
            col = (i % 2) * 2
            name_label = QLabel(metric)
            name_label.setFont(QFont("Microsoft YaHei", 10))
            self.metrics_grid.addWidget(name_label, row, col)
            value_label = QLabel(value)
            value_label.setFont(QFont("Microsoft YaHei", 10))
            value_label.setStyleSheet("color: #2980B9;")
            self.metrics_grid.addWidget(value_label, row, col + 1)
            self.metric_labels[key] = value_label

        layout.addLayout(self.metrics_grid)

        health_metrics_label = QLabel("<b>健康监测指标</b>")
        health_metrics_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        health_metrics_label.setStyleSheet("padding: 15px 0 8px 0; color: #2E86C1;")
        layout.addWidget(health_metrics_label)

        health_container = QWidget()
        health_container_layout = QHBoxLayout(health_container)
        health_container_layout.setSpacing(40)

        left_column = QVBoxLayout()
        right_column = QVBoxLayout()

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
            item_layout = QHBoxLayout()
            item_layout.setSpacing(10)
            name_label = QLabel(label)
            name_label.setFont(QFont("Microsoft YaHei", 9))
            name_label.setStyleSheet("font-weight: bold; min-width: 80px;")
            item_layout.addWidget(name_label)
            value_label = QLabel(f"- {unit}")
            value_label.setFont(QFont("Microsoft YaHei", 9))
            value_label.setStyleSheet("min-width: 90px;")
            item_layout.addWidget(value_label)
            min_val, max_val, _ = self.health_ranges.get(key, (0, 0, ""))
            range_label = QLabel(f"[正常范围: {min_val}-{max_val}]")
            range_label.setFont(QFont("Microsoft YaHei", 8))
            range_label.setStyleSheet("color: #7F8C8D; font-style: italic;")
            item_layout.addWidget(range_label)
            item_layout.addStretch(1)
            if i < len(health_items) // 2:
                left_column.addLayout(item_layout)
            else:
                right_column.addLayout(item_layout)
            self.health_labels[f"{key}_value"] = value_label

        health_container_layout.addLayout(left_column)
        health_container_layout.addSpacing(30)
        health_container_layout.addLayout(right_column)
        layout.addWidget(health_container)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #ccc; margin: 20px 0;")
        layout.addWidget(separator)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)

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
        layout = QHBoxLayout()
        layout.setSpacing(10)
        file_label = QLabel(label)
        file_label.setFont(QFont("Microsoft YaHei", 10))
        file_label.setFixedWidth(100)
        layout.addWidget(file_label)
        path_input = QLineEdit()
        path_input.setReadOnly(True)
        path_input.setFont(QFont("Microsoft YaHei", 9))
        path_input.setStyleSheet("padding: 6px; background-color: #F8F9F9; border: 1px solid #D6DBDF;")
        layout.addWidget(path_input, 1)
        file_btn = QPushButton("选择文件")
        file_btn.setFont(QFont("Microsoft YaHei", 9))
        file_btn.setStyleSheet("""
        QPushButton {
            background-color: #3498DB;
            color: white;
            padding: 8px 15px;
            border-radius: 4px;
            font-weight: bold;
            border: none;
        }
        QPushButton:hover {
            background-color: #2980B9;
        }
        QPushButton:pressed {
            background-color: #1F618D;
            padding: 7px 14px 9px 16px;
        }
        QPushButton:disabled {
            background-color: #AAB7B8;
        }
        """)
        file_btn.clicked.connect(lambda: self.select_file(file_filter, path_input, slot_name))
        layout.addWidget(file_btn)
        return layout

    def select_file(self, file_filter, path_input, slot_name):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", f"CSV文件 ({file_filter})")
        if file_path:
            path_input.setText(file_path)
            getattr(self, slot_name)(file_path)

    def health_data_selected(self, file_path):
        self.health_data_path = file_path
        self.status_edit.setText(f"已选择健康检测文件: {os.path.basename(file_path)}")
        self.process_health_data()

    def eeg_data_selected(self, file_path):
        self.eeg_data_path = file_path
        self.status_edit.setText(f"已选择脑电检测文件: {os.path.basename(file_path)}")
        self.process_eeg_data()

    def filter_abnormal_data(self, df, column, min_val=0, max_val=None):
        df_filtered = df[df[column] >= min_val]
        if max_val is not None:
            df_filtered = df_filtered[df_filtered[column] <= max_val]
        return df_filtered

    def process_health_data(self):
        if not self.health_data_path:
            self.status_edit.setText("请选择健康检测数据文件")
            return
        try:
            health_df = pd.read_csv(self.health_data_path)
            health_file = os.path.basename(self.health_data_path)
            parts = health_file.split('_')
            if len(parts) >= 3:
                health_date = parts[-2]
                health_time = parts[-1].split('.')[0]
            else:
                raise ValueError(f"健康监测文件名格式不正确: {health_file}")
            date_display = f"{health_date[:4]}-{health_date[4:6]}-{health_date[6:8]}"
            health_time_display = f"{health_time[:2]}:{health_time[2:4]}:{health_time[4:6]}"
            health_df['Timestamp'] = pd.to_datetime(health_df['Timestamp'], errors='coerce')
            health_df = self.filter_abnormal_data(health_df, 'HeartRate', 40, 200)
            health_df = self.filter_abnormal_data(health_df, 'BloodOxygen', 70, 100)
            health_df = self.filter_abnormal_data(health_df, 'Temperature', 35, 42)
            health_df = self.filter_abnormal_data(health_df, 'RespirationRate', 5, 60)
            health_df = self.filter_abnormal_data(health_df, 'AmbientTemp', -10, 50)
            health_df = self.filter_abnormal_data(health_df, 'Fatigue', 0, 100)
            health_df = self.filter_abnormal_data(health_df, 'SystolicBP', 60, 200)
            health_df = self.filter_abnormal_data(health_df, 'DiastolicBP', 40, 120)
            heart_rate_avg = health_df['HeartRate'].mean()
            blood_oxygen_avg = health_df['BloodOxygen'].mean()
            temperature_avg = health_df['Temperature'].mean()
            respiration_rate_avg = health_df['RespirationRate'].mean()
            ambient_temp_avg = health_df['AmbientTemp'].mean()
            systolic_bp_avg = health_df['SystolicBP'].mean()
            diastolic_bp_avg = health_df['DiastolicBP'].mean()
            fatigue_avg = health_df['Fatigue'].mean()
            self.health_metrics = {
                "heart_rate": heart_rate_avg,
                "blood_oxygen": blood_oxygen_avg,
                "temperature": temperature_avg,
                "respiration_rate": respiration_rate_avg,
                "ambient_temp": ambient_temp_avg,
                "systolic_bp": systolic_bp_avg,
                "diastolic_bp": diastolic_bp_avg,
                "fatigue": fatigue_avg
            }
            self.update_health_metrics(self.health_metrics)
            self.status_edit.setText(f"健康数据已处理: {os.path.basename(self.health_data_path)}")
        except Exception as e:
            self.status_edit.setText(f"健康数据处理错误: {str(e)}")
            import traceback
            traceback.print_exc()

    def process_eeg_data(self):
        if not self.eeg_data_path:
            self.status_edit.setText("请选择脑电检测数据文件")
            return
        try:
            self.report_data = None
            self.status_edit.setText("正在处理脑电数据...")
            QApplication.processEvents()
            eeg_file = os.path.basename(self.eeg_data_path)
            eeg_df = pd.read_csv(self.eeg_data_path)
            required_columns = ['Epoch_Index', 'Sleep_Stage', 'Stage_Label']
            missing_columns = [col for col in required_columns if col not in eeg_df.columns]
            if missing_columns:
                raise ValueError(f"数据文件缺少必要列: {', '.join(missing_columns)}")
            valid_stages = {0: 'W', 1: 'N1', 2: 'N2', 3: 'N3', 4: 'REM'}
            eeg_df = eeg_df[eeg_df['Sleep_Stage'].isin(valid_stages.keys())].copy()
            eeg_df['Stage_Name'] = eeg_df['Sleep_Stage'].map(valid_stages)
            if len(eeg_df) == 0:
                unique_stages = sorted(eeg_df['Sleep_Stage'].unique())
                raise ValueError(f"未找到有效睡眠阶段数据。文件中的睡眠阶段值为: {unique_stages}")
            metrics = self.calculate_sleep_metrics(eeg_df)
            self.report_data = {
                "sleep_duration": metrics['total_sleep_time'],
                "deep_sleep": metrics['deep_sleep_percent'],
                "light_sleep": metrics['light_sleep_percent'],
                "rem_sleep": metrics['rem_sleep_percent'],
                "sleep_latency": metrics['sleep_latency'],
                "awakenings": metrics['awakenings'],
                "sleep_efficiency": metrics['sleep_efficiency'],
                "sleep_score": metrics['sleep_score'],
                "user_info": f"数据文件: {eeg_file} | 有效记录数: {len(eeg_df)}",
                "records_count": f"{len(eeg_df)}条有效记录"
            }
            self.update_data_display()
            self.status_edit.setText(f"成功处理脑电数据: {os.path.basename(self.eeg_data_path)}")
        except Exception as e:
            error_msg = f"脑电数据处理错误: {str(e)}"
            self.status_edit.setText(error_msg)
            print(error_msg)
            import traceback
            traceback.print_exc()

    def calculate_sleep_metrics(self, df):
        if 'Stage_Name' not in df.columns:
            valid_stages = {0: 'W', 1: 'N1', 2: 'N2', 3: 'N3', 4: 'REM'}
            df['Stage_Name'] = df['Sleep_Stage'].map(valid_stages).fillna('UNK')
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
        total_epochs = len(df)
        sleep_latency = self.calculate_sleep_latency(df)
        sleep_data = df[df['Stage_Name'] != 'W']
        sleep_minutes = len(sleep_data) * 0.5
        total_minutes = total_epochs * 0.5
        sleep_efficiency = (sleep_minutes / total_minutes) * 100 if total_minutes > 0 else 0
        stage_minutes = {
            'W': len(df[df['Stage_Name'] == 'W']) * 0.5,
            'N1': len(df[df['Stage_Name'] == 'N1']) * 0.5,
            'N2': len(df[df['Stage_Name'] == 'N2']) * 0.5,
            'N3': len(df[df['Stage_Name'] == 'N3']) * 0.5,
            'REM': len(df[df['Stage_Name'] == 'REM']) * 0.5
        }
        awaken_events = self.calculate_awakenings(df)
        sleep_score = self.calculate_sleep_score(
            sleep_efficiency, stage_minutes['N3'], stage_minutes['REM'], sleep_latency, awaken_events, total_minutes)
        return {
            'total_minutes': total_minutes,
            'total_sleep_time': sleep_minutes / 60,
            'sleep_latency': sleep_latency,
            'sleep_efficiency': sleep_efficiency,
            'deep_sleep_percent': (stage_minutes['N3'] / sleep_minutes * 100) if sleep_minutes > 0 else 0,
            'light_sleep_percent': ((stage_minutes['N1'] + stage_minutes['N2']) / sleep_minutes * 100) if sleep_minutes > 0 else 0,
            'rem_sleep_percent': (stage_minutes['REM'] / sleep_minutes * 100) if sleep_minutes > 0 else 0,
            'awakenings': awaken_events,
            'sleep_score': sleep_score
        }

    def calculate_sleep_latency(self, df):
        consecutive_sleep = 0
        latency = 0
        for i, row in df.iterrows():
            latency += 0.5
            if row['Stage_Name'] != 'W':
                consecutive_sleep += 0.5
            else:
                consecutive_sleep = 0
            if consecutive_sleep >= 5.0:
                return latency - 5.0
        return latency

    def calculate_awakenings(self, df):
        awaken_events = 0
        in_wake_period = False
        consecutive_wake = 0
        for row in df['Stage_Name']:
            if row == 'W':
                consecutive_wake += 0.5
                if not in_wake_period and consecutive_wake >= 5:
                    awaken_events += 1
                    in_wake_period = True
            else:
                consecutive_wake = 0
                in_wake_period = False
        return awaken_events

    def calculate_sleep_score(self, efficiency, deep_minutes, rem_minutes, latency, awakenings, total_minutes):
        efficiency_weight = 0.35
        deep_weight = 0.25
        rem_weight = 0.15
        latency_weight = 0.15
        awakening_weight = 0.10
        efficiency_score = min(100, max(0, efficiency)) * efficiency_weight
        deep_percent = deep_minutes / total_minutes * 100
        deep_score = min(100, max(0, deep_percent * 4)) * deep_weight
        rem_percent = rem_minutes / total_minutes * 100
        rem_score = min(100, max(0, rem_percent * 4)) * rem_weight
        if latency <= 10:
            latency_score = 100
        elif latency <= 30:
            latency_score = 100 - (latency - 10) * 4
        else:
            latency_score = 20
        latency_score *= latency_weight
        if awakenings == 0:
            awakening_score = 100
        elif awakenings <= 2:
            awakening_score = 80
        elif awakenings <= 4:
            awakening_score = 60
        else:
            awakening_score = 30
        awakening_score *= awakening_weight
        total_score = efficiency_score + deep_score + rem_score + latency_score + awakening_score
        if total_minutes < 240:
            total_score *= 0.8
        return min(100, max(0, total_score))

    def process_data(self):
        if self.health_data_path:
            self.process_health_data()
        if self.eeg_data_path:
            self.process_eeg_data()
        if self.health_metrics is not None and self.report_data is not None:
            result_window = AssessmentResultWindow(self.report_data, self.health_metrics, self.health_ranges, self)
            result_window.exec_()
        else:
            self.status_edit.setText("数据处理失败，无法显示评估结果")

    def update_data_display(self):
        if not self.report_data:
            return

        # 定义睡眠指标的单位
        sleep_units = {
            "sleep_duration": "小时",
            "deep_sleep": "%",
            "light_sleep": "%",
            "rem_sleep": "%",
            "sleep_latency": "分钟",
            "awakenings": "次",
            "sleep_efficiency": "%",
            "sleep_score": "/100"
        }

        # 格式化并设置每个指标的值
        for key, label in self.metric_labels.items():
            value = self.report_data.get(key)
            if value is not None:
                # 根据不同数据类型进行格式化
                if key == "sleep_score":
                    formatted_value = f"{value:.0f}{sleep_units.get(key, '')}"
                elif key == "sleep_latency":
                    formatted_value = f"{value:.1f}{sleep_units.get(key, '')}"
                elif key == "awakenings":
                    formatted_value = f"{int(value)}{sleep_units.get(key, '')}"
                else:
                    formatted_value = f"{value:.1f}{sleep_units.get(key, '')}"

                label.setText(formatted_value)

        # 特殊格式化和样式
        self.metric_labels["sleep_efficiency"].setStyleSheet("color: #27AE60; font-weight: bold;")
        self.metric_labels["sleep_score"].setStyleSheet("color: #2980B9; font-weight: bold;")

    def update_health_metrics(self, health_metrics):
        for key, value in health_metrics.items():
            min_val, max_val, unit = self.health_ranges.get(key, (0, 0, ""))
            if pd.isna(value):
                value_str = "N/A"
            elif isinstance(value, float):
                value_str = f"{value:.1f}"
            else:
                value_str = f"{value}"
            self.health_labels[f"{key}_value"].setText(f"{value_str} {unit}")
            if min_val <= value <= max_val:
                self.health_labels[f"{key}_value"].setStyleSheet("color: #27AE60; font-weight: bold;")
            else:
                self.health_labels[f"{key}_value"].setStyleSheet("color: #E74C3C; font-weight: bold;")

    def export_report(self):
        if not self.report_data:
            self.status_edit.setText("Please process the data first to generate a report.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Report",
            f"Sleep_Quality_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return  # 用户取消操作

        # 确保健康指标存在，如果不存在则设为空字典
        health_metrics = self.health_metrics if self.health_metrics else {}

        try:
            # 创建报告生成器
            report_generator = PDFReportGenerator(self.report_data, health_metrics, self.health_ranges)

            # 生成报告
            success, message = report_generator.generate_report(file_path)

            if success:
                self.status_edit.setText(message)
            else:
                self.status_edit.setText(message)
        except Exception as e:
            self.status_edit.setText(f"Report generation failed: {str(e)}")
            import traceback
            traceback.print_exc()

    def closeEvent(self, event):
        super().closeEvent(event)
        if self.parent() and hasattr(self.parent(), 'on_sleep_assessment_closed'):
            self.parent().on_sleep_assessment_closed()
        event.accept()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = SleepAssessmentWindow()
    window.show()
    sys.exit(app.exec_())