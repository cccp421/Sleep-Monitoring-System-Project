from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QComboBox, QFrame, QAction)
import pyqtgraph as pg
from serial_worker import SerialWorker
from dashboard import DashboardTab
from collections import deque


class TGAMGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TGAM 脑电数据采集系统")
        self.setGeometry(100, 100, 1200, 900)  # 增大窗口尺寸以适应新布局

        # 初始化UI
        self.init_ui()

        # 初始化串口工作线程
        self.serial_worker = SerialWorker()

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

        # 串口选择下拉框
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        toolbar.addWidget(QLabel("串口:"))
        toolbar.addWidget(self.port_combo)

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        toolbar.addWidget(self.refresh_btn)

        # 连接按钮
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.connect_btn.clicked.connect(self.connect_device)
        toolbar.addWidget(self.connect_btn)

        # 断开按钮
        self.disconnect_btn = QPushButton("断开")
        self.disconnect_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.disconnect_btn.clicked.connect(self.disconnect_device)
        self.disconnect_btn.setEnabled(False)  # 初始时禁用断开按钮
        toolbar.addWidget(self.disconnect_btn)

        # 主内容区域
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)  # 使用水平布局
        main_layout.setSpacing(10)

        # 左侧仪表盘区域
        self.dashboard_tab = DashboardTab()

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
        right_layout.addWidget(waveform_frame, 1)  # 使用比例因子
        right_layout.addWidget(spectrum_frame, 1)

        # 添加左右部分到主布局
        main_layout.addWidget(self.dashboard_tab, 1)  # 仪表盘占用1/5空间
        main_layout.addWidget(right_container, 4)  # 波形和频谱占用4/5空间

        # 状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪，请选择串口并连接设备")

    def connect_signals(self):
        """连接信号和槽函数"""
        # 串口工作线程信号
        self.serial_worker.raw_data_ready.connect(self.update_waveform)
        self.serial_worker.large_package_ready.connect(self.update_dashboard)
        self.serial_worker.stats_updated.connect(self.update_stats)
        self.serial_worker.connection_failed.connect(self.connection_failed)
        self.serial_worker.connection_success.connect(self.connection_success)
        self.serial_worker.port_list_updated.connect(self.update_port_list)

    def refresh_ports(self):
        """刷新可用串口列表"""
        self.serial_worker.refresh_ports()

    def update_port_list(self, ports):
        """更新串口下拉列表"""
        self.port_combo.clear()
        self.port_combo.addItems(ports)

    def connect_device(self):
        """连接设备"""
        port = self.port_combo.currentText()
        if not port:
            self.status_bar.showMessage("请选择串口", 3000)
            return

        self.status_bar.showMessage(f"正在连接 {port}...")
        self.serial_worker.set_port(port)
        self.serial_worker.start()

        # 在连接过程中禁用连接按钮
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)

        # 清除旧数据
        self.clear_data()

    def disconnect_device(self):
        """断开设备连接"""
        self.serial_worker.stop()
        self.dashboard_tab.connection_status.setText("<b style='color:red;'>断开连接</b>")
        self.status_bar.showMessage("设备已断开")

        # 断开连接后启用连接按钮，禁用断开按钮
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)

        # 清除所有数据和图形状态
        self.clear_data()

    def clear_data(self):
        """清除所有数据和图形状态"""
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

    def connection_success(self):
        """连接成功处理"""
        self.dashboard_tab.connection_status.setText("<b style='color:green;'>已连接</b>")
        self.status_bar.showMessage("连接成功，等待数据...")

        # 连接成功后禁用连接按钮，启用断开按钮
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)

        # 重置时间轴起点
        self.plot_widget.setXRange(0, 7)

    def connection_failed(self, message):
        """连接失败处理"""
        self.dashboard_tab.connection_status.setText("<b style='color:red;'>连接失败</b>")
        self.status_bar.showMessage(f"连接失败: {message}", 5000)

        # 连接失败后启用连接按钮，禁用断开按钮
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)

        # 清除旧数据
        self.clear_data()

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
            f"<b style='font-size:14pt;'>{large_data['meditation']}</b>")  # 修正这里

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
        event.accept()