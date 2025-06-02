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