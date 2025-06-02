# tgam_gui.py
import sys
import csv
import time
from datetime import datetime
from collections import deque
import serial
import serial.tools.list_ports
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
                             QStatusBar, QAction, QTabWidget, QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QColor
import pyqtgraph as pg


class SerialWorker(QThread):
    # 定义信号
    raw_data_ready = pyqtSignal(int, float)
    large_package_ready = pyqtSignal(dict)
    stats_updated = pyqtSignal(dict)
    connection_failed = pyqtSignal(str)
    connection_success = pyqtSignal()
    port_list_updated = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ser = None
        self.running = False
        self.port = None
        self.baudrate = 57600
        self.raw_file = None
        self.raw_writer = None
        self.timer = QTimer()

    def set_port(self, port):
        self.port = port

    def run(self):
        """主串口读取和处理线程"""
        if not self.port:
            self.connection_failed.emit("没有选择串口")
            return

        # 尝试连接串口
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,  # 短超时防止阻塞
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            self.connection_success.emit()
        except serial.SerialException as e:
            self.connection_failed.emit(str(e))
            return

        # 创建原始数据文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.raw_filename = f"tgam_rawdata_{timestamp}.csv"

        try:
            self.raw_file = open(self.raw_filename, 'w', newline='')
            self.raw_writer = csv.writer(self.raw_file)
            self.raw_writer.writerow(["Timestamp", "RawValue"])
        except Exception as e:
            error_msg = f"无法创建数据文件: {str(e)}"
            self.connection_failed.emit(error_msg)
            return

        # 初始化统计变量
        self.start_time = time.time()
        self.last_time = self.start_time
        self.total_packages = 0
        self.valid_packages = 0
        self.invalid_count = 0
        self.state = 0  # 0: 等待同步, 1: 已接收第一个AA, 2: 正在接收包
        self.package_buffer = []  # 数据包缓冲区
        self.latest_large_data = None

        self.running = True

        # 初始同步状态 - 等待AA AA开始
        synced = False
        while self.running and not synced:
            if self.ser.in_waiting > 0:
                byte = self.ser.read(1)[0]  # 读取单个字节

                if self.state == 0:
                    if byte == 0xAA:
                        self.state = 1

                elif self.state == 1:
                    if byte == 0xAA:
                        self.state = 2  # 已接收同步头
                        synced = True
                    else:
                        self.state = 0
            else:
                time.sleep(0.1)

        if not synced:
            self.connection_failed.emit("无法同步数据")
            self.stop()
            return

        # 主循环处理数据
        while self.running:
            # 读取串口数据
            bytes_to_read = self.ser.in_waiting
            if bytes_to_read == 0:
                time.sleep(0.001)  # 减少CPU占用
                continue

            data = self.ser.read(bytes_to_read)
            current_time = time.time()
            timestamp_str = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

            # 处理每个字节
            for byte in data:
                byte_value = byte

                # 状态机处理数据包
                if self.state == 2:  # 正在接收数据包
                    self.package_buffer.append(byte_value)

                    # 检查包长度是否足够判断包类型
                    if len(self.package_buffer) >= 3:
                        # 小包固定长度8字节
                        if self.package_buffer[2] == 0x04 and len(self.package_buffer) == 8:
                            self.total_packages += 1

                            # 解析数据包
                            rawdata = self.parse_small_package(self.package_buffer)

                            if rawdata is not None:
                                self.valid_packages += 1

                                # 保存原始数据到文件
                                self.raw_writer.writerow([timestamp_str, rawdata])

                                # 发出原始数据信号
                                self.raw_data_ready.emit(rawdata, current_time - self.start_time)

                            else:
                                self.invalid_count += 1

                            # 重置状态寻找下一个包
                            self.package_buffer = []
                            self.state = 0

                        # 大包处理（长度字节为0x20，即32字节payload）
                        elif self.package_buffer[2] == 0x20:  # 大包标识
                            # 大包总长度 = 同步头(2) + 长度(1) + payload(32) + 校验和(1) = 36字节
                            if len(self.package_buffer) == 36:
                                # 解析大包
                                large_data = self.parse_large_package(self.package_buffer)
                                if large_data is not None:
                                    # 存储最新的大包数据
                                    self.latest_large_data = large_data
                                    # 发出大包数据信号
                                    self.large_package_ready.emit(large_data)

                                # 重置状态寻找下一个包
                                self.package_buffer = []
                                self.state = 0

                        # 其他长度的包（可能是数据损坏）
                        elif len(self.package_buffer) > 50:  # 防止无限增长
                            self.package_buffer = []
                            self.state = 0

                # 重新同步过程
                if self.state == 0:
                    if byte_value == 0xAA:
                        self.package_buffer = [byte_value]
                        self.state = 1

                elif self.state == 1:
                    if byte_value == 0xAA:
                        self.package_buffer.append(byte_value)
                        self.state = 2
                    else:
                        self.state = 0

            # 每200毫秒发送一次统计信息
            if current_time - self.last_time >= 0.2:
                stats = {
                    'total_packages': self.total_packages,
                    'valid_packages': self.valid_packages,
                    'invalid_count': self.invalid_count,
                    'start_time': self.start_time,
                    'running_time': current_time - self.start_time
                }
                self.stats_updated.emit(stats)
                self.last_time = current_time

    def stop(self):
        """停止串口线程"""
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        if self.raw_file:
            self.raw_file.close()
        self.wait()

    def parse_small_package(self, package):
        """解析小包数据并验证校验和"""
        if len(package) != 8:
            return None

        # 检查包头格式 (AA AA 04 80 02)
        if package[0] != 0xAA or package[1] != 0xAA:
            return None
        if package[2] != 0x04 or package[3] != 0x80 or package[4] != 0x02:
            return None

        # 提取数据部分
        xx_high = package[5]
        xx_low = package[6]
        xx_checksum = package[7]

        # 计算校验和
        calculated_sum = 0x80 + 0x02 + xx_high + xx_low
        calculated_checksum = (~calculated_sum) & 0xFF

        if calculated_checksum != xx_checksum:
            return None  # 校验失败

        # 计算原始数据
        rawdata = (xx_high << 8) | xx_low
        if rawdata > 32768:
            rawdata -= 65536

        return rawdata

    def parse_large_package(self, package):
        """解析大包数据（信号强度、专注度、放松度和EEG功率值）"""
        # 包格式：AA AA [长度] [payload] [校验和]
        # 大包总长度 = 同步头(2) + 长度(1) + payload(L) + 校验和(1)
        if len(package) < 4:
            return None

        # 提取长度字节（payload长度）
        payload_length = package[2]

        # 检查包长度是否有效
        if len(package) != 3 + payload_length + 1:  # 3(同步头+长度) + payload + 校验和
            return None

        # 验证同步头
        if package[0] != 0xAA or package[1] != 0xAA:
            return None

        # 提取payload部分
        payload = package[3:3 + payload_length]

        # 计算校验和
        payload_sum = sum(payload) & 0xFF
        calculated_checksum = (~payload_sum) & 0xFF

        # 实际校验和是最后一个字节
        actual_checksum = package[-1]

        if calculated_checksum != actual_checksum:
            return None  # 校验失败

        # 初始化结果字典
        result = {
            'signal': 0,  # 信号强度
            'attention': 0,  # 专注度
            'meditation': 0,  # 放松度
            'eeg_power': [0] * 8  # 8个EEG功率值
        }

        # 解析payload中的各个部分
        index = 0
        while index < len(payload):
            code = payload[index]
            index += 1

            if code == 0x02:  # 信号强度
                if index < len(payload):
                    result['signal'] = payload[index]
                    index += 1

            elif code == 0x83:  # EEG Power 开始
                # 下一个字节是EEG数据长度
                if index >= len(payload):
                    break
                eeg_length = payload[index]
                index += 1

                # 验证EEG数据长度
                if eeg_length != 24:  # 24字节用于8个EEG值(每个3字节)
                    index += eeg_length  # 跳过
                    continue

                # 读取EEG数据
                if index + eeg_length > len(payload):
                    break

                eeg_data = payload[index:index + eeg_length]
                index += eeg_length

                # 解析8个EEG功率值 (每3字节一组)
                for i in range(8):
                    start_idx = i * 3
                    if start_idx + 2 < len(eeg_data):
                        # 每个值由3字节组成：高字节、中字节、低字节
                        high = eeg_data[start_idx]
                        mid = eeg_data[start_idx + 1]
                        low = eeg_data[start_idx + 2]

                        # 组合成32位值
                        value = (high << 16) | (mid << 8) | low
                        result['eeg_power'][i] = value

            elif code == 0x04:  # 专注度
                if index < len(payload):
                    result['attention'] = payload[index]
                    index += 1

            elif code == 0x05:  # 放松度
                if index < len(payload):
                    result['meditation'] = payload[index]
                    index += 1

            else:
                # 未知代码，跳过
                if index < len(payload):
                    index += 1

        return result

    def refresh_ports(self):
        """刷新可用串口列表"""
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.port_list_updated.emit(port_list)


class TGAMGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TGAM 脑电数据采集系统")
        self.setGeometry(100, 100, 1200, 800)

        # 初始化UI
        self.init_ui()

        # 初始化串口工作线程
        self.serial_worker = SerialWorker()

        # 连接信号和槽
        self.connect_signals()

        # 刷新串口列表
        self.refresh_ports()

        # 初始化数据缓冲区
        self.raw_data = deque(maxlen=1000)
        self.time_data = deque(maxlen=1000)

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

        # 串口选择下拉框
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        toolbar.addWidget(QLabel("串口:"))
        toolbar.addWidget(self.port_combo)

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        toolbar.addWidget(self.refresh_btn)

        # 连接/断开按钮
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.connect_btn.clicked.connect(self.toggle_connection)
        toolbar.addWidget(self.connect_btn)

        # 主内容区域
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # 创建选项卡
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # 创建仪表盘选项卡
        self.dashboard_tab = QWidget()
        self.tabs.addTab(self.dashboard_tab, "仪表盘")

        # 创建波形选项卡
        self.waveform_tab = QWidget()
        self.tabs.addTab(self.waveform_tab, "波形显示")

        # 创建EEG频谱选项卡
        self.eeg_tab = QWidget()
        self.tabs.addTab(self.eeg_tab, "EEG频谱")

        # 设置仪表盘布局
        self.setup_dashboard()

        # 设置波形显示布局
        self.setup_waveform()

        # 设置EEG频谱布局
        self.setup_eeg_spectrum()

        # 状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪，请选择串口并连接设备")

    def setup_dashboard(self):
        """设置仪表盘布局"""
        layout = QHBoxLayout(self.dashboard_tab)

        # 左侧状态面板
        status_group = QGroupBox("设备状态")
        status_layout = QFormLayout()

        self.connection_status = QLabel("<b style='color:red;'>断开连接</b>")
        status_layout.addRow(QLabel("连接状态:"), self.connection_status)

        self.signal_strength = QLabel("-")
        status_layout.addRow(QLabel("信号强度:"), self.signal_strength)

        self.attention_value = QLabel("-")
        status_layout.addRow(QLabel("专注度:"), self.attention_value)

        self.meditation_value = QLabel("-")
        status_layout.addRow(QLabel("放松度:"), self.meditation_value)

        status_group.setLayout(status_layout)

        # 统计信息面板
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

        # EEG功率表
        eeg_group = QGroupBox("EEG功率值")
        eeg_layout = QVBoxLayout()

        self.eeg_table = QTableWidget(8, 2)
        self.eeg_table.setHorizontalHeaderLabels(["频段", "功率值"])
        self.eeg_table.verticalHeader().setVisible(False)
        self.eeg_table.setColumnWidth(0, 150)
        self.eeg_table.setColumnWidth(1, 150)

        # 设置频段名称
        bands = ["Delta", "Theta", "Low Alpha", "High Alpha",
                 "Low Beta", "High Beta", "Low Gamma", "Middle Gamma"]
        for i, band in enumerate(bands):
            item = QTableWidgetItem(band)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.eeg_table.setItem(i, 0, item)

            item = QTableWidgetItem("-")
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.eeg_table.setItem(i, 1, item)

        eeg_layout.addWidget(self.eeg_table)
        eeg_group.setLayout(eeg_layout)

        # 添加控件到布局
        left_layout = QVBoxLayout()
        left_layout.addWidget(status_group)
        left_layout.addWidget(stats_group)
        left_layout.addStretch()

        right_layout = QVBoxLayout()
        right_layout.addWidget(eeg_group)

        layout.addLayout(left_layout, 1)
        layout.addLayout(right_layout, 2)

    def setup_waveform(self):
        """设置波形显示布局"""
        layout = QVBoxLayout(self.waveform_tab)

        # 创建波形图
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setTitle("原始脑电波形", color='k', size="12pt")
        self.plot_widget.setLabel('left', '振幅')
        self.plot_widget.setLabel('bottom', '时间 (秒)')
        self.plot_widget.showGrid(x=True, y=True)

        # 设置X轴范围
        self.plot_widget.setXRange(0, 5)

        # 创建曲线
        self.curve = self.plot_widget.plot(pen='b')

        layout.addWidget(self.plot_widget)

    def setup_eeg_spectrum(self):
        """设置EEG频谱显示布局"""
        layout = QVBoxLayout(self.eeg_tab)

        # 创建频谱图
        self.spectrum_widget = pg.PlotWidget()
        self.spectrum_widget.setBackground('w')
        self.spectrum_widget.setTitle("EEG功率谱", color='k', size="12pt")
        self.spectrum_widget.setLabel('left', '功率值')
        self.spectrum_widget.setLabel('bottom', '频段')

        # 创建柱状图
        self.bars = pg.BarGraphItem(x=range(8), height=[0] * 8, width=0.6)
        self.spectrum_widget.addItem(self.bars)

        # 设置Y轴范围
        self.spectrum_widget.setYRange(0, 100000)

        # 设置X轴标签
        x_axis = self.spectrum_widget.getAxis('bottom')
        bands = ["Delta", "Theta", "Low Alpha", "High Alpha",
                 "Low Beta", "High Beta", "Low Gamma", "Mid Gamma"]
        x_axis.setTicks([[(i, bands[i]) for i in range(8)]])

        layout.addWidget(self.spectrum_widget)

    def connect_signals(self):
        """连接信号和槽函数"""
        # 串口工作线程信号
        self.serial_worker.raw_data_ready.connect(self.update_waveform)
        self.serial_worker.large_package_ready.connect(self.update_dashboard)
        self.serial_worker.stats_updated.connect(self.update_stats)
        self.serial_worker.connection_failed.connect(self.connection_failed)
        self.serial_worker.connection_success.connect(self.connection_success)
        self.serial_worker.port_list_updated.connect(self.update_port_list)

        # UI按钮信号
        self.connect_btn.clicked.connect(self.toggle_connection)

    def refresh_ports(self):
        """刷新可用串口列表"""
        self.serial_worker.refresh_ports()

    def update_port_list(self, ports):
        """更新串口下拉列表"""
        self.port_combo.clear()
        self.port_combo.addItems(ports)

    def toggle_connection(self):
        """切换连接状态"""
        if self.connect_btn.text() == "连接":
            self.connect_device()
        else:
            self.disconnect_device()

    def connect_device(self):
        """连接设备"""
        port = self.port_combo.currentText()
        if not port:
            self.status_bar.showMessage("请选择串口", 3000)
            return

        self.status_bar.showMessage(f"正在连接 {port}...")
        self.serial_worker.set_port(port)
        self.serial_worker.start()

    def disconnect_device(self):
        """断开设备连接"""
        self.serial_worker.stop()
        self.connection_status.setText("<b style='color:red;'>断开连接</b>")
        self.connect_btn.setText("连接")
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.status_bar.showMessage("设备已断开")

    def connection_success(self):
        """连接成功处理"""
        self.connection_status.setText("<b style='color:green;'>已连接</b>")
        self.connect_btn.setText("断开")
        self.connect_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.status_bar.showMessage("连接成功，等待数据...")

    def connection_failed(self, message):
        """连接失败处理"""
        self.connection_status.setText("<b style='color:red;'>连接失败</b>")
        self.status_bar.showMessage(f"连接失败: {message}", 5000)

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
        self.signal_strength.setText(self.get_signal_text(large_data['signal']))
        self.attention_value.setText(f"<b style='font-size:14pt;'>{large_data['attention']}</b>")
        self.meditation_value.setText(f"<b style='font-size:14pt;'>{large_data['meditation']}</b>")

        # 更新EEG表格
        for i, value in enumerate(large_data['eeg_power']):
            item = QTableWidgetItem(str(value))
            item.setTextAlignment(Qt.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.eeg_table.setItem(i, 1, item)

        # 更新频谱图
        heights = [v for v in large_data['eeg_power']]
        max_val = max(heights) if any(heights) else 1
        heights = [h * 100000 / max_val for h in heights]  # 归一化
        self.bars.setOpts(height=heights)

    def get_signal_text(self, signal_value):
        """获取信号强度的文本表示"""
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

        self.running_time.setText(f"{int(hours)}:{int(mins):02d}:{int(secs):02d}")
        self.packets_received.setText(str(stats['total_packages']))
        self.valid_packets.setText(str(stats['valid_packages']))

        if stats['running_time'] > 0:
            packet_rate = stats['valid_packages'] / stats['running_time']
            self.packet_rate.setText(f"{packet_rate:.1f}/s")

            if stats['total_packages'] > 0:
                loss_percent = (stats['total_packages'] - stats['valid_packages']) / stats['total_packages'] * 100
                self.loss_percent.setText(f"{loss_percent:.2f}%")

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
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = TGAMGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()