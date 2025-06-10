from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QComboBox, QFrame, QAction, QGroupBox, QGridLayout)
from PyQt5.QtSerialPort import QSerialPortInfo
import pyqtgraph as pg
from serial_worker import SerialWorker, HealthWorker
from dashboard import DashboardTab
from collections import deque
from sleep_assessment import SleepAssessmentWindow  # 导入新的睡眠评估窗口
import time

class TGAMGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SMS 脑电与健康数据采集系统")
        self.setGeometry(100, 100, 1400, 900)  # 增大窗口尺寸以适应新布局

        # 初始化UI
        self.init_ui()

        # 初始化串口工作线程
        self.serial_worker = SerialWorker()
        self.health_worker = HealthWorker()

        # 连接信号和槽
        self.connect_signals()

        # 刷新串口列表
        self.refresh_ports()

        # 初始化数据缓冲区
        self.raw_data = deque(maxlen=4000)
        self.time_data = deque(maxlen=4000)

    def init_ui(self):
        """初始化用户界面"""
        sleep_assessment_action = QAction('睡眠质量评估', self)
        sleep_assessment_action.triggered.connect(self.open_sleep_assessment)

        # 创建工具栏
        toolbar = self.addToolBar('控制')

        # 脑电串口选择
        toolbar.addWidget(QLabel("脑电接口:"))
        self.eeg_port_combo = QComboBox()
        self.eeg_port_combo.setMinimumWidth(150)
        toolbar.addWidget(self.eeg_port_combo)

        # 健康设备串口选择
        toolbar.addWidget(QLabel("健康接口:"))
        self.health_port_combo = QComboBox()
        self.health_port_combo.setMinimumWidth(150)
        toolbar.addWidget(self.health_port_combo)

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新所有")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        toolbar.addWidget(self.refresh_btn)

        # 脑电连接按钮
        self.connect_eeg_btn = QPushButton("连接脑电设备")
        self.connect_eeg_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.connect_eeg_btn.clicked.connect(self.connect_eeg_device)
        toolbar.addWidget(self.connect_eeg_btn)

        # 脑电断开按钮
        self.disconnect_eeg_btn = QPushButton("断开脑电设备")
        self.disconnect_eeg_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.disconnect_eeg_btn.clicked.connect(self.disconnect_eeg_device)
        self.disconnect_eeg_btn.setEnabled(False)
        toolbar.addWidget(self.disconnect_eeg_btn)

        # 健康设备连接按钮
        self.connect_health_btn = QPushButton("连接健康设备")
        self.connect_health_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.connect_health_btn.clicked.connect(self.connect_health_device)
        toolbar.addWidget(self.connect_health_btn)

        # 健康设备断开按钮
        self.disconnect_health_btn = QPushButton("断开健康设备")
        self.disconnect_health_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.disconnect_health_btn.clicked.connect(self.disconnect_health_device)
        self.disconnect_health_btn.setEnabled(False)
        toolbar.addWidget(self.disconnect_health_btn)

        # 新增睡眠评估按钮
        self.sleep_assessment_btn = QPushButton("睡眠质量评估")
        self.sleep_assessment_btn.setStyleSheet("background-color: #6A5ACD; color: white;")
        self.sleep_assessment_btn.clicked.connect(self.open_sleep_assessment)
        toolbar.addWidget(self.sleep_assessment_btn)
        toolbar.addSeparator()  # 添加分隔符

        # 主内容区域
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 使用垂直布局替代水平布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)

        # 上部容器（波形图和仪表盘）
        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧仪表盘区域
        self.dashboard_tab = DashboardTab()
        top_layout.addWidget(self.dashboard_tab, 1)  # 左侧仪表盘占比1份

        # 右侧波形显示区域
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        # 波形显示
        waveform_frame = QFrame()
        waveform_frame.setFrameShape(QFrame.StyledPanel)
        waveform_layout = QVBoxLayout(waveform_frame)
        waveform_layout.setContentsMargins(0, 0, 0, 0)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setTitle("原始脑电波形", color='k', size="12pt")
        self.plot_widget.setLabel('left', '振幅')
        self.plot_widget.setLabel('bottom', '时间 (秒)')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setXRange(0, 7)
        self.curve = self.plot_widget.plot(pen='b')
        waveform_layout.addWidget(self.plot_widget)

        # 添加波形图到右侧区域（高度减半）
        right_layout.addWidget(waveform_frame, 1)  # 波形图占右侧区域50%高度

        top_layout.addWidget(right_container, 4)  # 右侧波形图区域占比4份
        main_layout.addWidget(top_container, 1)  # 上部区域整体占比50%

        # 下部健康数据窗口 (占整个窗口下半部分)
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)

        # 健康数据分组框 - 使用更大的标题和字体
        health_group = QGroupBox("健康监测数据")
        health_group.setStyleSheet("QGroupBox { font-size: 14pt; font-weight: bold; }")
        health_layout = QGridLayout(health_group)
        health_layout.setSpacing(15)  # 增加间距

        # 健康数据指标 - 添加更多标签
        health_indicators = [
            ("心率:", "heart_rate_value", "bpm"),
            ("血氧饱和度:", "spo2_value", "%"),
            ("收缩压(高压):", "systolic_bp_value", "mmHg"),
            ("舒张压(低压):", "diastolic_bp_value", "mmHg"),
            ("呼吸频率:", "respiration_rate_value", "次/分"),
            ("体温:", "temperature_value", "°C"),
            ("环境温度:", "ambient_temp_value", "°C"),
            ("疲劳指数:", "fatigue_value", ""),
            ("RR间期:", "rr_value", "ms"),
            ("HRV-SDNN:", "hrv_sdnn_value", "ms"),
            ("HRV-RMSSD:", "hrv_rmssd_value", "ms"),
            ("微循环:", "microcirculation_value", "")
        ]

        # 添加健康数据标签 - 使用更大的字体
        for i, (label_text, value_name, unit) in enumerate(health_indicators):
            row = i // 3  # 每行3个指标
            col = (i % 3) * 3

            # 标签
            label = QLabel(f"<b>{label_text}</b>")
            label.setStyleSheet("font-size: 12pt;")
            health_layout.addWidget(label, row, col)

            # 值
            value_label = QLabel("-")
            value_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1E90FF;")
            setattr(self, value_name, value_label)
            health_layout.addWidget(value_label, row, col + 1)

            # 单位
            unit_label = QLabel(unit)
            unit_label.setStyleSheet("font-size: 10pt;")
            health_layout.addWidget(unit_label, row, col + 2)

        # 添加健康数据到下部区域
        bottom_layout.addWidget(health_group)
        main_layout.addWidget(bottom_container, 1)  # 下部健康数据占比50%

        # 状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪，请选择串口并连接设备")

        # 睡眠评估窗口
        self.sleep_assessment_window = None

    def open_sleep_assessment(self):
        """打开睡眠质量评估窗口前停止数据采集"""
        # 首先停止脑电设备
        if self.serial_worker.isRunning():
            self.disconnect_eeg_device()  # 调用断开连接方法

        # 然后停止健康设备
        if self.health_worker.isRunning():
            self.disconnect_health_device()  # 调用断开连接方法

        # 双重确保所有设备已停止
        if self.serial_worker.isRunning():
            self.serial_worker.stop()
            self.serial_worker.wait(1000)  # 等待1秒确保线程停止
        if self.health_worker.isRunning():
            self.health_worker.stop()
            self.health_worker.wait(1000)

        # 更新状态栏
        self.status_bar.showMessage("已停止数据采集，打开睡眠质量评估...")

        # 现在打开睡眠评估窗口
        if self.sleep_assessment_window is None:
            self.sleep_assessment_window = SleepAssessmentWindow(self)
            self.sleep_assessment_window.show()
            self.status_bar.showMessage("已打开睡眠质量评估窗口")
        else:
            # 如果窗口已经存在，则将其置顶
            self.sleep_assessment_window.activateWindow()
            self.sleep_assessment_window.raise_()

    def on_sleep_assessment_closed(self):
        """睡眠评估窗口关闭时的回调函数"""
        self.sleep_assessment_window = None
        self.status_bar.showMessage("睡眠评估窗口已关闭")

    def connect_signals(self):
        """连接信号和槽函数"""
        # 脑电设备信号
        self.serial_worker.raw_data_ready.connect(self.update_waveform)
        self.serial_worker.large_package_ready.connect(self.update_dashboard)
        self.serial_worker.stats_updated.connect(self.update_stats)
        self.serial_worker.connection_failed.connect(self.eeg_connection_failed)
        self.serial_worker.connection_success.connect(self.eeg_connection_success)
        self.serial_worker.port_list_updated.connect(self.update_port_list)

        # 健康设备信号
        self.health_worker.health_data_ready.connect(self.update_health_data)
        self.health_worker.connection_status.connect(self.health_connection_status)

    def refresh_ports(self):
        """刷新可用串口列表"""
        self.serial_worker.refresh_ports()

        # 同时刷新健康设备串口列表
        ports = [port.portName() for port in QSerialPortInfo.availablePorts()]
        self.health_port_combo.clear()
        self.health_port_combo.addItems(ports)
        if ports:
            self.health_port_combo.setCurrentIndex(0)

    def update_port_list(self, ports):
        """更新串口下拉列表"""
        self.eeg_port_combo.clear()
        self.eeg_port_combo.addItems(ports)

    def connect_eeg_device(self):
        """连接脑电设备"""
        port = self.eeg_port_combo.currentText()
        if not port:
            self.status_bar.showMessage("请选择脑电串口", 3000)
            return

        self.status_bar.showMessage(f"正在连接脑电设备 {port}...")
        self.serial_worker.set_port(port)
        self.serial_worker.start()

        # 在连接过程中禁用连接按钮
        self.connect_eeg_btn.setEnabled(False)
        self.disconnect_eeg_btn.setEnabled(True)

        # 清除旧数据
        self.clear_eeg_data()

    def disconnect_eeg_device(self):
        """断开脑电设备连接并确保数据保存"""
        self.serial_worker.stop()
        self.dashboard_tab.connection_status.setText("<b style='color:red;'>断开连接</b>")
        self.status_bar.showMessage("脑电设备已断开，数据已保存")

        # 更新按钮状态
        self.connect_eeg_btn.setEnabled(True)
        self.disconnect_eeg_btn.setEnabled(False)

        # 清除UI上的脑电数据
        self.clear_eeg_data()

    def connect_health_device(self):
        """连接健康检测设备"""
        port = self.health_port_combo.currentText()
        if not port:
            self.status_bar.showMessage("请选择健康设备串口", 3000)
            return

        self.status_bar.showMessage(f"正在连接健康设备 {port}...")
        self.health_worker.set_port(port)
        self.health_worker.start()

        # 更新按钮状态
        self.connect_health_btn.setEnabled(False)
        self.disconnect_health_btn.setEnabled(True)

    def disconnect_health_device(self):
        """断开健康检测设备连接并确保停止"""
        # 发送停止命令
        self.health_worker.send_stop_command()

        # 等待500ms确保命令发送
        time.sleep(0.5)

        # 断开设备连接
        self.health_worker.stop()
        self.status_bar.showMessage("健康设备已断开，数据已保存")

        # 重置健康数据显示
        self.reset_health_data()

        # 更新按钮状态
        self.connect_health_btn.setEnabled(True)
        self.disconnect_health_btn.setEnabled(False)

    def clear_eeg_data(self):
        """清除脑电数据"""
        # 清空数据缓冲区
        self.raw_data.clear()
        self.time_data.clear()

        # 重置波形图
        self.curve.setData([], [])

        # 重置仪表盘状态
        self.dashboard_tab.signal_strength.setText("-")
        self.dashboard_tab.attention_value.setText("-")
        self.dashboard_tab.meditation_value.setText("-")

        # 重置时间轴范围
        self.plot_widget.setXRange(0, 7)

    def reset_health_data(self):
        """重置健康数据显示"""
        self.heart_rate_value.setText("-")
        self.spo2_value.setText("-")
        self.systolic_bp_value.setText("-")
        self.diastolic_bp_value.setText("-")
        self.respiration_rate_value.setText("-")
        self.temperature_value.setText("-")
        self.ambient_temp_value.setText("-")
        self.fatigue_value.setText("-")
        self.rr_value.setText("-")
        self.hrv_sdnn_value.setText("-")
        self.hrv_rmssd_value.setText("-")
        self.microcirculation_value.setText("-")

    def eeg_connection_success(self):
        """脑电设备连接成功处理"""
        self.dashboard_tab.connection_status.setText("<b style='color:green;'>已连接</b>")
        self.status_bar.showMessage("脑电设备连接成功，等待数据...")

        # 连接成功后禁用连接按钮，启用断开按钮
        self.connect_eeg_btn.setEnabled(False)
        self.disconnect_eeg_btn.setEnabled(True)

        # 重置时间轴起点
        self.plot_widget.setXRange(0, 7)

    def eeg_connection_failed(self, message):
        """脑电设备连接失败处理"""
        self.dashboard_tab.connection_status.setText("<b style='color:red;'>连接失败</b>")
        self.status_bar.showMessage(f"脑电设备连接失败: {message}", 5000)

        # 连接失败后启用连接按钮，禁用断开按钮

        self.connect_eeg_btn.setEnabled(True)
        self.disconnect_eeg_btn.setEnabled(False)

        # 清除旧数据
        self.clear_eeg_data()

    def health_connection_status(self, message):
        """更新健康设备连接状态"""
        self.status_bar.showMessage(f"健康设备: {message}", 3000)

    def update_waveform(self, raw_data, timestamp):
        """更新波形显示"""
        self.raw_data.append(raw_data)
        self.time_data.append(timestamp)

        # 每100次更新一次波形图
        if len(self.raw_data) % 100 == 0 or len(self.raw_data) == 1:
            self.curve.setData(list(self.time_data), list(self.raw_data))

            # 如果数据超过当前X轴范围，自动滚动
            if timestamp > self.plot_widget.getViewBox().viewRange()[0][1]:
                self.plot_widget.setXRange(timestamp - 5, timestamp + 1)

    def update_dashboard(self, large_data):
        """更新仪表盘数据"""
        # 更新设备状态
        self.dashboard_tab.signal_strength.setText(self.get_signal_text(large_data['signal']))
        self.dashboard_tab.attention_value.setText(f"<b style='font-size:14pt;'>{large_data['attention']}</b>")
        self.dashboard_tab.meditation_value.setText(
            f"<b style='font-size:14pt;'>{large_data['meditation']}</b>")

        # 更新EEG功率值标签
        if len(large_data['eeg_power']) >= 8:
            self.dashboard_tab.delta_value.setText(str(large_data['eeg_power'][0]))
            self.dashboard_tab.theta_value.setText(str(large_data['eeg_power'][1]))
            self.dashboard_tab.low_alpha_value.setText(str(large_data['eeg_power'][2]))
            self.dashboard_tab.high_alpha_value.setText(str(large_data['eeg_power'][3]))
            self.dashboard_tab.low_beta_value.setText(str(large_data['eeg_power'][4]))
            self.dashboard_tab.high_beta_value.setText(str(large_data['eeg_power'][5]))
            self.dashboard_tab.low_gamma_value.setText(str(large_data['eeg_power'][6]))
            self.dashboard_tab.mid_gamma_value.setText(str(large_data['eeg_power'][7]))

    def update_health_data(self, health_data):
        """更新健康数据显示 - 修改以适配新添加的字段"""
        self.heart_rate_value.setText(f"{health_data['heart_rate']}")
        self.spo2_value.setText(f"{health_data['blood_oxygen']}")
        self.systolic_bp_value.setText(f"{health_data['systolic_bp']}")
        self.diastolic_bp_value.setText(f"{health_data['diastolic_bp']}")
        self.respiration_rate_value.setText(f"{health_data['respiration_rate']}")
        self.temperature_value.setText(f"{health_data['temperature']:.1f}")
        self.ambient_temp_value.setText(f"{health_data['ambient_temp']:.1f}")
        self.fatigue_value.setText(f"{health_data['fatigue']}")
        # 新添加的字段
        self.rr_value.setText(f"{health_data.get('rr_interval', 'N/A')}")
        self.hrv_sdnn_value.setText(f"{health_data.get('hrv_sdnn', 'N/A')}")
        self.hrv_rmssd_value.setText(f"{health_data.get('hrv_rmssd', 'N/A')}")
        self.microcirculation_value.setText(f"{health_data.get('microcirculation', 'N/A')}")

        # 在状态栏显示关键健康指标
        self.status_bar.showMessage(
            f"心率: {health_data['heart_rate']}bpm | "
            f"血氧: {health_data['blood_oxygen']}% | "
            f"血压: {health_data['systolic_bp']}/{health_data['diastolic_bp']}mmHg | "
            f"体温: {health_data['temperature']:.1f}°C"
        )

    def get_signal_text(self, signal_value):
        """获取噪声强度的文本表示"""
        if signal_value >= 200:
            return f"<b style='color:red;font-size:14pt;'>{signal_value} (检测失败)</b>"
        elif signal_value >= 51:
            return f"<b style='color:red;font-size:14pt;'>{signal_value} (极差)</b>"
        elif signal_value >= 26:
            return f"<b style='color:#FF9800;font-size:14pt;'>{signal_value} (差)</b>"
        elif signal_value >= 1:
            return f"<b style='color:#4CAF50;font-size:14pt;'>{signal_value} (良好)</b>"
        else:
            return f"<b style='color:#4CAF50;font-size:14pt;'>{signal_value} (极佳)</b>"

    def update_stats(self, stats):
        """更新统计信息"""
        running_time = stats['running_time']
        mins, secs = divmod(running_time, 60)
        hours, mins = divmod(mins, 60)

        self.dashboard_tab.running_time.setText(f"{int(hours)}:{int(mins):02d}:{int(secs):02d}")
        self.dashboard_tab.packets_received.setText(str(stats['total_packages']))
        self.dashboard_tab.valid_packets.setText(str(stats['valid_packages']))

        if stats['running_time'] > 0:
            packet_rate = stats['valid_packages'] / stats['running_time']
            self.dashboard_tab.packet_rate.setText(f"{packet_rate:.1f}/s")

            if stats['total_packages'] > 0:
                loss_percent = (stats['total_packages'] - stats['valid_packages']) / stats['total_packages'] * 100
                self.dashboard_tab.loss_percent.setText(f"{loss_percent:.2f}%")

                # 在状态栏显示包速率
                self.status_bar.showMessage(
                    f"包速率: {packet_rate:.1f}/s | 丢包率: {loss_percent:.2f}% | "
                    f"有效包: {stats['valid_packages']} | 总计包: {stats['total_packages']}"
                )

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        if self.serial_worker.isRunning():
            self.serial_worker.stop()
            self.serial_worker.wait(1000)

        if self.health_worker.isRunning():
            # 发送停止命令
            self.health_worker.send_stop_command()
            self.health_worker.stop()
            self.health_worker.wait(1000)

        # 关闭睡眠评估窗口
        if self.sleep_assessment_window:
            self.sleep_assessment_window.close()

        event.accept()

