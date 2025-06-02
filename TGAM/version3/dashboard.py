from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                             QGroupBox, QFormLayout)

class DashboardTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """初始化仪表盘布局"""
        layout = QVBoxLayout(self)  # 整体垂直布局

        # 设备状态面板（最上方）
        status_group = QGroupBox("设备状态")
        status_layout = QFormLayout()

        self.connection_status = QLabel("<b style='color:red;'>断开连接</b>")
        status_layout.addRow(QLabel("连接状态:"), self.connection_status)

        self.signal_strength = QLabel("-")
        status_layout.addRow(QLabel("噪声强度:"), self.signal_strength)

        self.attention_value = QLabel("-")
        status_layout.addRow(QLabel("专注度:"), self.attention_value)

        self.meditation_value = QLabel("-")
        status_layout.addRow(QLabel("放松度:"), self.meditation_value)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # EEG功率表面板（中间）- 使用表单布局
        eeg_group = QGroupBox("EEG功率值")
        eeg_layout = QFormLayout()

        # 为每个频段创建标签
        self.delta_value = QLabel("-")
        self.theta_value = QLabel("-")
        self.low_alpha_value = QLabel("-")
        self.high_alpha_value = QLabel("-")
        self.low_beta_value = QLabel("-")
        self.high_beta_value = QLabel("-")
        self.low_gamma_value = QLabel("-")
        self.mid_gamma_value = QLabel("-")

        # 添加频段标签到表单
        eeg_layout.addRow(QLabel("Delta:"), self.delta_value)
        eeg_layout.addRow(QLabel("Theta:"), self.theta_value)
        eeg_layout.addRow(QLabel("Low Alpha:"), self.low_alpha_value)
        eeg_layout.addRow(QLabel("High Alpha:"), self.high_alpha_value)
        eeg_layout.addRow(QLabel("Low Beta:"), self.low_beta_value)
        eeg_layout.addRow(QLabel("High Beta:"), self.high_beta_value)
        eeg_layout.addRow(QLabel("Low Gamma:"), self.low_gamma_value)
        eeg_layout.addRow(QLabel("Middle Gamma:"), self.mid_gamma_value)

        eeg_group.setLayout(eeg_layout)
        layout.addWidget(eeg_group)

        # 统计信息面板（最下方）
        stats_group = QGroupBox("统计信息")
        stats_layout = QFormLayout()

        self.running_time = QLabel("-")
        stats_layout.addRow(QLabel("运行时间:"), self.running_time)

        self.packets_received = QLabel("-")
        stats_layout.addRow(QLabel("接收包数:"), self.packets_received)

        self.valid_packets = QLabel("-")
        stats_layout.addRow(QLabel("有效包数:"), self.valid_packets)

        self.packet_rate = QLabel("-")
        stats_layout.addRow(QLabel("包速率:"), self.packet_rate)

        self.loss_percent = QLabel("-")
        stats_layout.addRow(QLabel("丢包率:"), self.loss_percent)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # 添加伸缩因子使布局更灵活
        layout.addStretch(1)