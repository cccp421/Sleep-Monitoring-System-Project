from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QGridLayout, QFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class SleepAssessmentWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("睡眠质量评估")
        # 调整窗口尺寸为更紧凑的比例
        self.setGeometry(300, 200, 700, 520)

        # 设置窗口属性
        self.setWindowModality(Qt.ApplicationModal)  # 设置为模态窗口，当打开时主窗口不可用
        self.setAttribute(Qt.WA_DeleteOnClose)  # 关闭时自动删除

        # 初始化UI
        self.init_ui()

    def init_ui(self):
        """初始化睡眠评估界面 - 无滚动条的紧凑布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)  # 减小间距
        layout.setContentsMargins(30, 20, 30, 20)  # 减小边距

        # 标题
        title_label = QLabel("睡眠质量评估报告")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))  # 减小标题字体
        title_label.setStyleSheet("color: #2E86C1; padding: 5px;")
        layout.addWidget(title_label)

        # 简介信息
        info_label = QLabel(
            "此模块用于睡眠质量的综合评估\n\n"
            "步骤: 连接设备 → 选择时间 → 开始评估 → 查看结果"
        )
        info_label.setFont(QFont("Microsoft YaHei", 9))
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("background-color: #F8F9F9; border: 1px solid #D6DBDF; padding: 10px;")
        layout.addWidget(info_label)

        # 评估指标区
        metrics_label = QLabel("<b>评估指标</b>")
        metrics_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        metrics_label.setStyleSheet("padding: 10px 0 5px 0;")
        layout.addWidget(metrics_label)

        # 网格布局展示指标 - 更紧凑
        metrics_grid = QGridLayout()
        metrics_grid.setHorizontalSpacing(15)
        metrics_grid.setVerticalSpacing(8)

        metrics = [
            ("睡眠总时长:", "7.5小时"),
            ("深睡眠比例:", "28% (推荐15-25%)"),
            ("浅睡眠比例:", "50% (正常)"),
            ("REM睡眠比例:", "22% (推荐20-25%)"),
            ("入睡时间:", "23分钟 (正常)"),
            ("觉醒次数:", "2次 (正常)"),
            ("睡眠效率:", "93% (优秀)"),
            ("睡眠质量得分:", "88/100 (良好)")
        ]

        for i, (metric, value) in enumerate(metrics):
            row = i // 2  # 每行2列
            col = (i % 2) * 2

            name_label = QLabel(metric)
            name_label.setFont(QFont("Microsoft YaHei", 9))
            metrics_grid.addWidget(name_label, row, col)

            value_label = QLabel(value)
            value_label.setFont(QFont("Microsoft YaHei", 9))
            value_label.setStyleSheet("color: #2980B9;")
            metrics_grid.addWidget(value_label, row, col + 1)

        layout.addLayout(metrics_grid)

        # 分隔线
        separator = QLabel()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #ddd; margin: 10px 0;")
        layout.addWidget(separator)

        # 建议区域
        suggestion_label = QLabel("<b>健康建议</b>")
        suggestion_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        suggestion_label.setStyleSheet("padding: 10px 0 5px 0;")
        layout.addWidget(suggestion_label)

        # 建议内容
        suggestions = QLabel(
            "● 深睡眠时间略长，可能表示身体需要额外恢复\n"
            "● 睡眠整体质量良好，继续保持当前的睡眠习惯\n"
            "● 建议保持相同睡眠作息时间\n"
            "● 睡前避免摄入咖啡因或长时间使用电子产品"
        )
        suggestions.setFont(QFont("Microsoft YaHei", 9))
        suggestions.setStyleSheet("background-color: #FEF9E7; border: 1px solid #F7DC6F; padding: 10px;")
        layout.addWidget(suggestions)

        # 功能按钮占位区
        buttons_label = QLabel("<center>此处将放置控制按钮: 导入数据, 开始评估, 导出报告等</center>")
        buttons_label.setFont(QFont("Microsoft YaHei", 9))
        buttons_label.setStyleSheet("color: #7D6608; background-color: #FCF3CF; padding: 8px; margin-top: 15px;")
        layout.addWidget(buttons_label)

        # 状态显示
        self.status_label = QLabel("就绪，等待开始评估")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Microsoft YaHei", 9))
        self.status_label.setStyleSheet("padding: 8px; border-top: 1px solid #ddd; margin-top: 10px;")
        layout.addWidget(self.status_label)

    def closeEvent(self, event):
        """窗口关闭时清理资源并通知父窗口"""
        super().closeEvent(event)  # 调用父类的事件处理
        # 通知父窗口我们已经关闭了
        if self.parent() and hasattr(self.parent(), 'on_sleep_assessment_closed'):
            self.parent().on_sleep_assessment_closed()
        event.accept()