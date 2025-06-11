from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QFrame, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class AssessmentResultWindow(QDialog):
    def __init__(self, sleep_metrics, health_metrics, health_ranges, parent=None):
        super().__init__(parent)
        self.setWindowTitle("睡眠质量评估报告")
        self.setGeometry(400, 300, 600, 500)

        # 存储健康指标范围用于后续建议生成
        self.health_ranges = health_ranges
        self.health_metrics = health_metrics

        # 添加中英指标名称映射
        self.metric_names = {
            # 睡眠指标
            "sleep_duration": "睡眠时长",
            "deep_sleep": "深睡眠占比",
            "light_sleep": "浅睡眠占比",
            "rem_sleep": "REM睡眠占比",
            "sleep_latency": "入睡耗时",
            "awakenings": "夜醒次数",
            "sleep_efficiency": "睡眠效率",
            "sleep_score": "睡眠评分",

            # 健康指标
            "heart_rate": "心率",
            "blood_oxygen": "血氧饱和度",
            "temperature": "体温",
            "fatigue": "疲劳指数",
            "systolic_bp": "收缩压",
            "diastolic_bp": "舒张压",
            "ambient_temp": "环境温度",
            "respiration_rate": "呼吸频率",
            "rr_interval": "RR间期",
            "hrv_sdnn": "HRV-SDNN",
            "hrv_rmssd": "HRV-RMSSD",
            "microcirculation": "微循环",
        }

        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("睡眠质量评估报告")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        layout.addWidget(title_label)

        # Sleep Metrics Section
        sleep_section = QFrame()
        sleep_layout = QVBoxLayout(sleep_section)
        sleep_layout.addWidget(QLabel("<b>评估指标</b>"))

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

        for key, value in sleep_metrics.items():
            if key in ["sleep_duration", "deep_sleep", "light_sleep", "rem_sleep",
                       "sleep_latency", "awakenings", "sleep_efficiency", "sleep_score"]:
                # 格式化值
                formatted_value = self.format_sleep_metric_value(key, value)
                unit = sleep_units.get(key, "")
                # 使用中文字段名
                name_cn = self.metric_names.get(key, key)
                label = QLabel(f"{name_cn}: {formatted_value}{unit}")
                sleep_layout.addWidget(label)

        layout.addWidget(sleep_section)

        # Health Metrics Section - 只显示超出正常范围的指标
        health_section = QFrame()
        health_layout = QVBoxLayout(health_section)
        health_layout.addWidget(QLabel("<b>健康监测指标（异常值）</b>"))

        # 用于存储异常指标的变量，用于后续建议生成
        self.abnormal_indicators = {}

        for key, value in health_metrics.items():
            if key in health_ranges:
                min_val, max_val, unit = health_ranges[key]
                if not (min_val <= value <= max_val):
                    # 存储异常指标用于后续建议
                    self.abnormal_indicators[key] = {
                        'value': value,
                        'min': min_val,
                        'max': max_val,
                        'unit': unit
                    }
                    # 格式化显示值
                    value_str = f"{value:.1f}" if isinstance(value, float) else str(value)
                    # 确定是偏高还是偏低
                    status = "偏高" if value > max_val else "偏低"
                    # 使用中文字段名
                    name_cn = self.metric_names.get(key, key)
                    label_text = f"{name_cn}: {value_str}{unit} {status} [正常范围: {min_val}-{max_val}{unit}]"
                    label = QLabel(label_text)
                    label.setStyleSheet("color: red;")
                    health_layout.addWidget(label)

        # 如果没有异常指标，显示提示
        if not self.abnormal_indicators:
            label = QLabel("所有健康指标均在正常范围内")
            label.setStyleSheet("color: green;")
            health_layout.addWidget(label)

        layout.addWidget(health_section)

        # Suggestions Section
        suggestions_section = QFrame()
        suggestions_layout = QVBoxLayout(suggestions_section)
        suggestions_layout.addWidget(QLabel("<b>睡眠评估建议</b>"))
        suggestions_text = self.generate_suggestions(sleep_metrics)
        suggestions_label = QLabel(suggestions_text)
        suggestions_label.setWordWrap(True)
        suggestions_layout.addWidget(suggestions_label)
        layout.addWidget(suggestions_section)

    def format_sleep_metric_value(self, key, value):
        """格式化睡眠指标值"""
        # 对于"awakenings"指标，不需要小数位
        if key == "awakenings":
            return f"{int(value)}"
        # 对于"sleep_score"指标，显示整数（因为分数通常为整数）
        elif key == "sleep_score":
            return f"{int(value)}"
        # 其他指标保留一位小数
        return f"{value:.1f}"

    def generate_suggestions(self, sleep_metrics):
        suggestions = []

        # 直接获取睡眠评分（浮点数）
        sleep_score = sleep_metrics.get("sleep_score", 0)

        # 1. 睡眠环境建议
        suggestions.append("请确保睡前减少光照和噪音干扰，例如使用遮光窗帘或耳塞。")

        # 2. 睡眠习惯建议
        sleep_duration = sleep_metrics.get("sleep_duration", 0)
        if sleep_duration < 7:
            suggestions.append(f"您的睡眠时间（{sleep_duration:.1f}小时）不足，建议每晚保持7-9小时睡眠。")
        elif sleep_duration > 9:
            suggestions.append(f"您的睡眠时间（{sleep_duration:.1f}小时）过长，建议保持7-9小时睡眠。")
        suggestions.append("建议睡前避免剧烈运动和使用电子设备，以帮助入睡。")

        # 3. 睡眠阶段建议
        deep_sleep = sleep_metrics.get("deep_sleep", 0)
        rem_sleep = sleep_metrics.get("rem_sleep", 0)

        if deep_sleep < 15:
            suggestions.append(f"您的深睡眠比例（{deep_sleep:.1f}%）偏低，建议优化睡眠环境和作息习惯。")
        if rem_sleep < 20:
            suggestions.append(f"您的REM睡眠比例（{rem_sleep:.1f}%）偏低，建议改善睡前习惯。")

        # 4. 健康指标异常建议
        for key, info in self.abnormal_indicators.items():
            value = info['value']
            unit = info['unit']
            min_val = info['min']
            max_val = info['max']

            value_str = f"{value:.1f}{unit}" if isinstance(value, float) else f"{value}{unit}"

            # 获取中文名称
            name_cn = self.metric_names.get(key, key)

            # 为每个异常指标生成特定建议
            if key == "heart_rate":
                if value > max_val:
                    suggestions.append(f"心率偏高（{value_str}），建议咨询医生。")
                else:
                    suggestions.append(f"心率偏低（{value_str}），建议适度运动并注意休息。")

            elif key == "blood_oxygen":
                if value < min_val:
                    suggestions.append(f"血氧饱和度偏低（{value_str}），建议保持室内通风并检查呼吸健康。")

            elif key == "temperature":
                if value > max_val:
                    suggestions.append(f"体温偏高（{value_str}），建议适当降温并多补充水分。")
                else:
                    suggestions.append(f"体温偏低（{value_str}），请注意保暖。")

            elif key == "fatigue":
                if value > max_val:
                    suggestions.append(f"疲劳指数偏高（{value_str}），建议合理安排休息时间，避免过度劳累。")

            elif key == "systolic_bp":
                if value > max_val:
                    suggestions.append(f"收缩压偏高（{value_str}），建议关注血压健康并咨询医生。")
                else:
                    suggestions.append(f"收缩压偏低（{value_str}），建议咨询医生。")

            elif key == "diastolic_bp":
                if value > max_val:
                    suggestions.append(f"舒张压偏高（{value_str}），建议关注血压健康并咨询医生。")
                else:
                    suggestions.append(f"舒张压偏低（{value_str}），建议咨询医生。")

            # 通用情况
            else:
                if value > max_val:
                    suggestions.append(f"{name_cn}偏高（{value_str}），建议关注。")
                else:
                    suggestions.append(f"{name_cn}偏低（{value_str}），建议关注。")

        # 5. 综合睡眠质量建议
        if sleep_score < 50:
            suggestions.append("您的睡眠质量严重不足，建议综合改善睡眠环境、作息习惯，并关注健康指标。")
        elif sleep_score < 70:
            suggestions.append("您的睡眠质量有待提升，建议调整睡眠环境和习惯，同时关注健康指标。")
        elif sleep_score >= 90:
            suggestions.append("您的睡眠质量非常优秀，请继续保持当前良好的生活习惯！")

        if not suggestions:
            suggestions.append("您的睡眠和健康指标均正常，请继续保持。")

        return "\n".join(suggestions)