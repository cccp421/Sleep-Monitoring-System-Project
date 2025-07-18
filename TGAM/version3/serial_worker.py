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
        """停止串口线程并确保文件关闭"""
        self.running = False

        # 关闭串口连接
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except:
                pass

        # 确保文件正确关闭
        if self.raw_file and not self.raw_file.closed:
            try:
                self.raw_file.flush()  # 确保所有数据写入磁盘
                os.fsync(self.raw_file.fileno())  # 强制同步到磁盘
                self.raw_file.close()
            except:
                pass

        # 最多等待500ms确保线程退出
        self.wait(500)

    def refresh_ports(self):
        """刷新可用串口列表"""
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.port_list_updated.emit(port_list)


class HealthWorker(QThread):
    """独立线程处理心率检测模块的数据"""
    health_data_ready = pyqtSignal(dict)
    connection_status = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.port_name = "COM4"
        self.serial_port = None
        self.running = False

        # 创建健康数据存储文件夹
        self.data_dir = "health_data"  # 文件夹名称
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        self.health_file = None
        self.health_writer = None

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
        # 创建健康数据文件 - 保存在指定文件夹中
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.health_filename = os.path.join(self.data_dir, f"health_data_{timestamp}.csv")

        try:
            self.health_file = open(self.health_filename, 'w', newline='')
            self.health_writer = csv.writer(self.health_file)
            # 写入CSV头行
            self.health_writer.writerow([
                "Timestamp", "HeartRate", "BloodOxygen", "Microcirculation",
                "SystolicBP", "DiastolicBP", "RespirationRate", "Fatigue",
                "RRInterval", "HRV_SDNN", "HRV_RMSSD", "Temperature", "AmbientTemp"
            ])
        except Exception as e:
            error_msg = f"无法创建健康数据文件: {str(e)}"
            self.connection_status.emit(error_msg)
            return

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

            # 记录健康数据的时间戳
            health_timestamp = None

            while self.running:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    buffer.extend(data)
                    last_received = time.time()
                    health_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

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
                            health_data = self.process_packet(packet)

                            # 保存健康数据到文件
                            self.save_health_data(health_timestamp, health_data)

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
        return health_data

    def save_health_data(self, timestamp, health_data):
        """保存健康数据到CSV文件"""
        if not self.health_writer:
            return

        try:
            self.health_writer.writerow([
                timestamp,
                health_data['heart_rate'],
                health_data['blood_oxygen'],
                health_data['microcirculation'],
                health_data['systolic_bp'],
                health_data['diastolic_bp'],
                health_data['respiration_rate'],
                health_data['fatigue'],
                health_data['rr_interval'],
                health_data['hrv_sdnn'],
                health_data['hrv_rmssd'],
                health_data['temperature'],
                health_data['ambient_temp']
            ])
        except Exception as e:
            self.connection_status.emit(f"保存健康数据出错: {str(e)}")

    def stop(self):
        """停止线程并确保资源释放"""
        self.running = False

        # 发送停止命令
        self.send_stop_command()

        # 确保健康数据文件正确关闭
        if self.health_file and not self.health_file.closed:
            try:
                self.health_file.flush()  # 确保所有数据写入磁盘
                os.fsync(self.health_file.fileno())  # 强制同步到磁盘
                self.health_file.close()
            except Exception as e:
                self.connection_status.emit(f"关闭健康数据文件失败: {str(e)}")

        # 关闭串口
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except:
                pass

        # 等待线程退出
        self.wait(500)