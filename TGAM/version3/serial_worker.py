import csv
import time
import os  # 添加os模块用于处理路径
from datetime import datetime
import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from dataparser import parse_small_package, parse_large_package


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

        # 创建数据存储文件夹
        self.data_dir = "raw_data"  # 文件夹名称
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

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

        # 创建原始数据文件 - 保存在指定文件夹中
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.raw_filename = os.path.join(self.data_dir, f"tgam_rawdata_{timestamp}.csv")  # 修改这里

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
                            rawdata = parse_small_package(self.package_buffer)

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
                                large_data = parse_large_package(self.package_buffer)
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

    def refresh_ports(self):
        """刷新可用串口列表"""
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.port_list_updated.emit(port_list)