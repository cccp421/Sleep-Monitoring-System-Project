from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QComboBox, QFrame, QAction, QGroupBox, QGridLayout)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtSerialPort import QSerialPortInfo
import pyqtgraph as pg
from serial_worker import SerialWorker
from dashboard import DashboardTab
from collections import deque
import serial
import time


class HealthWorker(QThread):
    """独立线程处理心率检测模块的数据"""
    health_data_ready = pyqtSignal(dict)
    connection_status = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.port_name = "COM4"
        self.serial_port = None
        self.running = False

    def set_port(self, port):
        self.port_name = port

    def send_start_command(self):
        """发送启动命令: 0x24"""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(b'\x24')
                self.connection_status.emit("已发送启动命令")
                return True
            except Exception as e:
                self.connection_status.emit(f"发送启动命令失败: {str(e)}")
        return False

    def send_stop_command(self):
        """发送停止命令: 0x2A"""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(b'\x2A')
                self.connection_status.emit("已发送停止命令")
                return True
            except Exception as e:
                self.connection_status.emit(f"发送停止命令失败: {str(e)}")
        return False

    def run(self):
        """主线程函数"""
        try:
            self.serial_port = serial.Serial(
                port=self.port_name,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            if not self.serial_port.is_open:
                self.serial_port.open()

            self.connection_status.emit("已连接")

            # 发送启动命令
            if self.send_start_command():
                self.running = True
            else:
                self.connection_status.emit("无法发送启动命令")
                return

            # 缓冲区处理包数据
            buffer = bytearray()
            last_received = time.time()

            while self.running:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    buffer.extend(data)
                    last_received = time.time()

                    # 处理包 (0xFF开头, 0xF1结尾)
                    while len(buffer) >= 24:
                        start_idx = buffer.find(b'\xFF')
                        if start_idx == -1:
                            buffer.clear()
                            break

                        if start_idx > 0:
                            buffer = buffer[start_idx:]

                        if len(buffer) < 24:
                            break

                        # 检查包尾
                        if buffer[23] == 0xF1:
                            # 解析数据包
                            packet = buffer[:24]
                            self.process_packet(packet)
                            buffer = buffer[24:]
                        else:
                            # 不是完整包，等待更多数据
                            break
                else:
                    # 检查连接超时
                    if time.time() - last_received > 5:
                        self.connection_status.emit("连接超时")
                        break
                    time.sleep(0.1)

        except Exception as e:
            self.connection_status.emit(f"错误: {str(e)}")
        finally:
            self.stop()

    def process_packet(self, packet):
        """解析24字节的数据包"""
        health_data = {
            'heart_rate': packet[2],  # 心率
            'blood_oxygen': packet[3],  # 血氧
            'microcirculation': packet[4],  # 微循环
            'systolic_bp': packet[5],  # 收缩压（高压）
            'diastolic_bp': packet[6],  # 舒张压（低压）
            'respiration_rate': packet[7],  # 呼吸频率
            'fatigue': packet[8],  # 疲劳值
            'rr_interval': packet[9],  # RR间期
            'hrv_sdnn': packet[10],  # HRV-SDNN
            'hrv_rmssd': packet[11],  # HRV-RMSSD
            'temperature': packet[12] + packet[13] / 100.0,  # 体温
            'ambient_temp': packet[14] + packet[15] / 100.0,  # 环境温度
        }
        self.health_data_ready.emit(health_data)

    def stop(self):
        """停止线程"""
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            # 发送停止命令
            self.send_stop_command()
            self.serial_port.close()
        self.wait(500)


class TGAMGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TGAM 脑电与健康数据采集系统")
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
        # 创建菜单栏
        menubar = self.menuBar()
        file_menu = menubar.addMenu('文件')

        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 创建工具栏
        toolbar = self.addToolBar('控制')

        # 脑电串口选择
        toolbar.addWidget(QLabel("脑电串口:"))
        self.eeg_port_combo = QComboBox()
        self.eeg_port_combo.setMinimumWidth(150)
        toolbar.addWidget(self.eeg_port_combo)

        # 健康设备串口选择
        toolbar.addWidget(QLabel("健康串口:"))
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

        # 主内容区域
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)  # 使用水平布局
        main_layout.setSpacing(10)

        # 左侧仪表盘区域
        self.dashboard_tab = DashboardTab()

        # 添加健康数据分组框
        health_group = QGroupBox("健康数据")
        health_layout = QGridLayout(health_group)

        # 健康数据指标
        health_indicators = [
            ("心率 (bpm):", "heart_rate_value"),
            ("血氧 (%):", "spo2_value"),
            ("收缩压:", "systolic_bp_value"),
            ("舒张压:", "diastolic_bp_value"),
            ("呼吸频率:", "respiration_rate_value"),
            ("体温 (°C):", "temperature_value"),
            ("环境温度 (°C):", "ambient_temp_value"),
            ("疲劳值:", "fatigue_value")
        ]

        # 添加健康数据标签
        for i, (label_text, value_name) in enumerate(health_indicators):
            row = i // 2
            col = (i % 2) * 2
            health_layout.addWidget(QLabel(label_text), row, col)
            value_label = QLabel("-")
            setattr(self, value_name, value_label)
            health_layout.addWidget(value_label, row, col + 1)

        # 将健康数据添加到仪表盘
        self.dashboard_tab.layout().addWidget(health_group)

        # 右侧区域 (波形和频谱)
        right_container = QFrame()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

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

        # EEG频谱显示
        spectrum_frame = QFrame()
        spectrum_frame.setFrameShape(QFrame.StyledPanel)
        spectrum_layout = QVBoxLayout(spectrum_frame)
        spectrum_layout.setContentsMargins(0, 0, 0, 0)

        self.spectrum_widget = pg.PlotWidget()
        self.spectrum_widget.setBackground('w')
        self.spectrum_widget.setTitle("EEG功率谱", color='k', size="12pt")
        self.spectrum_widget.setLabel('left', '功率值')
        self.spectrum_widget.setLabel('bottom', '频段')
        self.bars = pg.BarGraphItem(x=range(8), height=[0] * 8, width=0.6)
        self.spectrum_widget.addItem(self.bars)
        self.spectrum_widget.setYRange(0, 100000)
        bands = ["Delta", "Theta", "Low Alpha", "High Alpha",
                 "Low Beta", "High Beta", "Low Gamma", "Mid Gamma"]
        x_axis = self.spectrum_widget.getAxis('bottom')
        x_axis.setTicks([[(i, bands[i]) for i in range(8)]])
        spectrum_layout.addWidget(self.spectrum_widget)

        # 添加波形和频谱到右侧区域
        right_layout.addWidget(waveform_frame, 1)
        right_layout.addWidget(spectrum_frame, 1)

        # 添加左右部分到主布局
        main_layout.addWidget(self.dashboard_tab, 1)
        main_layout.addWidget(right_container, 4)

        # 状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪，请选择串口并连接设备")

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
        """断开脑电设备连接"""
        self.serial_worker.stop()
        self.dashboard_tab.connection_status.setText("<b style='color:red;'>断开连接</b>")
        self.status_bar.showMessage("脑电设备已断开")

        # 断开连接后启用连接按钮，禁用断开按钮
        self.connect_eeg_btn.setEnabled(True)
        self.disconnect_eeg_btn.setEnabled(False)

        # 清除所有数据和图形状态
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
        """断开健康检测设备连接"""
        # 发送停止命令
        self.status_bar.showMessage("正在发送停止命令...")

        # 断开设备连接
        self.health_worker.stop()
        self.status_bar.showMessage("健康设备已断开")

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

        # 重置频谱图
        self.bars.setOpts(height=[0] * 8)

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

        # 更新频谱图
        heights = [v for v in large_data['eeg_power']]
        max_val = max(heights) if any(heights) else 1
        heights = [h * 100000 / max_val for h in heights]  # 归一化
        self.bars.setOpts(height=heights)

    def update_health_data(self, health_data):
        """更新健康数据显示"""
        self.heart_rate_value.setText(f"<b>{health_data['heart_rate']}</b>")
        self.spo2_value.setText(f"<b>{health_data['blood_oxygen']}%</b>")
        self.systolic_bp_value.setText(f"<b>{health_data['systolic_bp']}</b>")
        self.diastolic_bp_value.setText(f"<b>{health_data['diastolic_bp']}</b>")
        self.respiration_rate_value.setText(f"<b>{health_data['respiration_rate']}</b>")
        self.temperature_value.setText(f"<b>{health_data['temperature']:.1f}°C</b>")
        self.ambient_temp_value.setText(f"<b>{health_data['ambient_temp']:.1f}°C</b>")
        self.fatigue_value.setText(f"<b>{health_data['fatigue']}</b>")

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

        event.accept()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    main_window = TGAMGUI()
    main_window.show()
    sys.exit(app.exec_())