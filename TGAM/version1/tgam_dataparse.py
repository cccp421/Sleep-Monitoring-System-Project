# main.py
import serial
import serial.tools.list_ports
import time
import sys
import csv
from datetime import datetime
from tgam_plotter import RealTimePlot  # 导入波形显示模块


def parse_small_package(package):
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


def parse_large_package(package):
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


def read_tgam_data(port, baudrate=57600, plotter=None):
    """读取并解析TGAM串口数据"""
    print(f"正在连接到串口: {port}, 波特率: {baudrate}")

    # 创建原始数据文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_filename = f"tgam_rawdata_{timestamp}.csv"

    print(f"原始数据将保存至: {raw_filename}")

    # 打开文件并准备写入
    raw_file = open(raw_filename, 'w', newline='')
    raw_writer = csv.writer(raw_file)
    raw_writer.writerow(["Timestamp", "RawValue"])

    # 统计变量
    state = 0  # 0: 等待同步, 1: 已接收第一个AA, 2: 正在接收包
    package_buffer = []  # 数据包缓冲区
    start_time = time.time()
    last_time = start_time
    last_large_time = start_time
    total_packages = 0
    valid_packages = 0
    invalid_count = 0
    data_available = False  # 是否已接收到有效数据

    # 最近解析出的大包数据
    latest_large_data = None

    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.1,  # 短超时防止阻塞
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        print("连接成功! 开始接收数据... (按Ctrl+C停止)")
        print("等待数据同步中...")

        # 初始同步状态 - 等待AA AA开始
        synced = False
        while not synced:
            if ser.in_waiting > 0:
                byte = ser.read(1)[0]  # 读取单个字节

                if state == 0:
                    if byte == 0xAA:
                        state = 1

                elif state == 1:
                    if byte == 0xAA:
                        state = 2  # 已接收同步头
                        synced = True
                        print("数据同步成功!")
                    else:
                        state = 0
            else:
                # 显示等待信息
                print(".", end="")
                sys.stdout.flush()
                time.sleep(0.1)

        start_time = time.time()
        print(f"\n开始接收时间: {time.strftime('%H:%M:%S')}")

        # 主循环处理数据
        while True:
            # 读取串口数据
            bytes_to_read = ser.in_waiting
            if bytes_to_read == 0:
                time.sleep(0.001)  # 减少CPU占用
                continue

            data = ser.read(bytes_to_read)

            current_time = time.time()
            timestamp_str = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

            # 处理每个字节
            for byte in data:
                byte_value = byte

                # 状态机处理数据包
                if state == 2:  # 正在接收数据包
                    package_buffer.append(byte_value)

                    # 检查包长度是否足够判断包类型
                    if len(package_buffer) >= 3:
                        # 小包固定长度8字节
                        if package_buffer[2] == 0x04 and len(package_buffer) == 8:
                            total_packages += 1

                            # 解析数据包
                            rawdata = parse_small_package(package_buffer)

                            if rawdata is not None:
                                valid_packages += 1
                                data_available = True

                                # 保存原始数据到文件
                                raw_writer.writerow([timestamp_str, rawdata])

                                # 添加到波形绘图
                                if plotter is not None:
                                    plotter.add_data(rawdata)

                                # 每秒更新统计信息
                                if current_time - last_time >= 1.0:
                                    elapsed = current_time - start_time
                                    package_rate = total_packages / elapsed
                                    valid_rate = valid_packages / elapsed

                                    # 计算丢包率
                                    if total_packages > 0:
                                        loss_percent = (total_packages - valid_packages) / total_packages * 100
                                    else:
                                        loss_percent = 0

                                    # 显示统计信息
                                    info = f"原始数据: {rawdata:6d} | 速率: {valid_rate:.1f}/s (目标:513) | "
                                    info += f"丢包: {loss_percent:.1f}% | 总计: {valid_packages} 包"

                                    # 如果有大包数据，也显示出来
                                    if latest_large_data is not None:
                                        current_large = latest_large_data
                                        # 确保每5秒显示一次完整的大包数据
                                        if current_time - last_large_time >= 5.0:
                                            bands = ["Delta", "Theta", "Low Alpha", "High Alpha",
                                                     "Low Beta", "High Beta", "Low Gamma", "Middle Gamma"]
                                            print("\n" + "-" * 80)
                                            print("大包数据:")
                                            print(f"信号强度: {current_large['signal']}")
                                            print(f"专注度: {current_large['attention']}")
                                            print(f"放松度: {current_large['meditation']}")
                                            print("\nEEG功率值:")
                                            for i in range(8):
                                                print(f"{bands[i]}: {current_large['eeg_power'][i]}")
                                            print("-" * 80)
                                            last_large_time = current_time

                                        # 在状态行中显示关键指标
                                        info += f" | SIG:{current_large['signal']} ATT:{current_large['attention']} MED:{current_large['meditation']}"

                                    sys.stdout.write("\r" + info)
                                    sys.stdout.flush()
                                    last_time = current_time
                            else:
                                invalid_count += 1

                            # 重置状态寻找下一个包
                            package_buffer = []
                            state = 0

                        # 大包处理（长度字节为0x20，即32字节payload）
                        elif package_buffer[2] == 0x20:  # 大包标识
                            # 大包总长度 = 同步头(2) + 长度(1) + payload(32) + 校验和(1) = 36字节
                            if len(package_buffer) == 36:
                                # 解析大包
                                large_data = parse_large_package(package_buffer)
                                if large_data is not None:
                                    # 存储最新的大包数据
                                    latest_large_data = large_data
                                else:
                                    # 大包解析失败
                                    pass

                                # 重置状态寻找下一个包
                                package_buffer = []
                                state = 0

                        # 其他长度的包（可能是数据损坏）
                        elif len(package_buffer) > 50:  # 防止无限增长
                            package_buffer = []
                            state = 0

                # 重新同步过程
                if state == 0:
                    if byte_value == 0xAA:
                        package_buffer = [byte_value]
                        state = 1

                elif state == 1:
                    if byte_value == 0xAA:
                        package_buffer.append(byte_value)
                        state = 2
                    else:
                        state = 0

    except serial.SerialException as e:
        print(f"\n串口错误: {e}")
        if "Permission denied" in str(e):
            print("\n权限问题解决方案:")
            print("  - Linux/Mac: sudo chmod a+rw 或 添加用户到dialout组")
            print("      sudo usermod -a -G dialout $USER")
            print("  - Windows: 确保您有访问COM端口的权限")
    except KeyboardInterrupt:
        print("\n用户终止程序")
    except Exception as e:
        print(f"\n发生未预期的错误: {e}")
    finally:
        # 关闭原始数据文件
        raw_file.close()
        print(f"\n原始数据已保存至: {raw_filename}")

        if 'ser' in locals() and ser.is_open:
            try:
                ser.close()
                print("\n串口已关闭")
            except:
                pass

        if data_available:
            elapsed = time.time() - start_time
            print("\n\n数据采集统计报告:")
            print(f"采集时长: {elapsed:.2f}秒")
            print(f"接收总包数: {total_packages}")
            print(f"有效数据包: {valid_packages} (速率: {valid_packages / elapsed:.1f}/s)")
            print(f"无效/损坏包: {total_packages - valid_packages}")

            if total_packages > 0:
                loss_percent = (total_packages - valid_packages) / total_packages * 100
                print(f"丢包率: {loss_percent:.2f}%")
                print("提示: 丢包率<10%属于正常范围，不影响脑电数据分析")
        else:
            print("\n警告: 未收到有效数据")

        # 如果有最后的大包数据，显示它
        if latest_large_data is not None:
            bands = ["Delta", "Theta", "Low Alpha", "High Alpha",
                     "Low Beta", "High Beta", "Low Gamma", "Middle Gamma"]
            print("\n" + "=" * 80)
            print("最后收到的大包数据:")
            print(f"信号强度: {latest_large_data['signal']}")
            print(f"专注度: {latest_large_data['attention']}")
            print(f"放松度: {latest_large_data['meditation']}")
            print("\nEEG功率值:")
            for i in range(8):
                print(f"{bands[i]}: {latest_large_data['eeg_power'][i]}")
            print("=" * 80)

        # 通知绘图器退出
        if plotter is not None:
            plotter.quit()


def manual_port_selection():
    """手动选择串口"""
    print("\n可用串口列表:")
    ports = serial.tools.list_ports.comports()

    if not ports:
        print("未检测到可用串口!")
        print("请检查连接并确保已安装驱动程序")
        return None, None

    for i, port in enumerate(ports):
        print(f"[{i + 1}] {port.device}: {port.description}")

    while True:
        try:
            choice = input("\n请输入串口号(1-{}) 或 手动输入串口路径: ".format(len(ports)))

            # 处理手动输入
            if choice.startswith("COM") or choice.startswith("/dev/"):
                return choice, 57600

            # 处理选择
            choice = int(choice)
            if 1 <= choice <= len(ports):
                port = ports[choice - 1].device
                return port, 57600
            else:
                print("无效选择，请重试")
        except ValueError:
            # 处理COM端口字符串
            if choice.upper().startswith("COM"):
                return choice, 57600
            print("请输入数字或有效串口路径")


if __name__ == "__main__":
    print("==== TGAM 脑电数据采集系统 ====")
    print("请手动选择串口连接TGAM设备")

    # 询问是否启用波形显示
    use_plot = input("是否启用实时波形显示? (y/n): ").lower() == 'y'

    # 启动绘图器（如果启用）
    plotter = None
    if use_plot:
        plotter = RealTimePlot(max_points=2000)
        print("实时波形显示已启动...")
        print("操作提示: P=暂停/继续, C=清屏, Q=退出")

    port, baud = manual_port_selection()

    if port:
        print(f"\n使用端口: {port}, 波特率: 57600")
        read_tgam_data(port, plotter=plotter)
    else:
        print("无法确定串口，程序退出")

    # 确保绘图器关闭
    if plotter is not None:
        plotter.quit()