import numpy as np
import pandas as pd
import os
import glob
import re

# ================================ 配置区域 ================================
# 输入设置
NPZ_DIR = "E:/DREAMT base/sleep-edf/sleep-edf-database-expanded-1.0.0/sleep-cassette/eeg_fpz_cz"  # 存放NPZ文件的目录

# 输出设置
OUTPUT_DIR = "E:/DREAMT base/sleep-edf/sleep-edf-database-expanded-1.0.0/sleep-cassette/csv_output"  # CSV输出目录

# 处理模式
SAVE_FULL_SEQUENCE = False  # True:保存完整时间序列, False:保存epoch统计特征


# ============================== 函数定义区域 ==============================
def parse_filename(filename):
    """解析文件名获取患者ID和记录ID"""
    base_name = os.path.basename(filename)

    # 尝试不同模式匹配
    patterns = [
        r"([A-Z]{2}\d+)-(\w+)\..*",  # SC4*和ST7*模式
        r"([A-Z]+-\d+)-(\w+)\..*",  # 带有连字符的ID模式
        r"([A-Za-z]+[\d_]+)_?(\w+)\.npz"  # 更通用的模式
    ]

    for pattern in patterns:
        match = re.match(pattern, base_name)
        if match:
            patient_id = match.group(1)
            record_id = match.group(2)
            return patient_id, record_id

    # 如果都匹配失败，提取文件名主体
    name_without_ext = os.path.splitext(base_name)[0]
    parts = name_without_ext.split('_')
    if len(parts) >= 2:
        return parts[0], '_'.join(parts[1:])
    return name_without_ext, "unknown"


def convert_npz_to_csv(npz_file, save_sequence=False):
    """将单个NPZ文件转换为CSV格式"""
    data = np.load(npz_file)

    # 解析基本信息
    patient_id, record_id = parse_filename(npz_file)
    sampling_rate = data['fs']
    epoch_duration = data['epoch_duration']
    n_samples = data['x'].shape[1]

    # 创建基础数据帧
    df_list = []

    for epoch_idx in range(len(data['y'])):
        # 提取时间序列数据点
        if save_sequence:
            for sample_idx in range(n_samples):
                time_offset = sample_idx / sampling_rate
                df_list.append([
                    patient_id,
                    record_id,
                    epoch_idx,
                    sample_idx,
                    time_offset,
                    data['x'][epoch_idx, sample_idx],
                    data['y'][epoch_idx]
                ])
        # 保存统计特征
        else:
            epoch_data = data['x'][epoch_idx]
            df_list.append([
                patient_id,
                record_id,
                epoch_idx,
                epoch_duration,
                np.mean(epoch_data),
                np.std(epoch_data),
                np.min(epoch_data),
                np.max(epoch_data),
                np.median(epoch_data),
                np.quantile(epoch_data, 0.25),  # 25百分位
                np.quantile(epoch_data, 0.75),  # 75百分位
                data['y'][epoch_idx]
            ])

    # 创建DataFrame
    if save_sequence:
        columns = [
            'Patient_ID', 'Record_ID', 'Epoch_Index', 'Sample_Index',
            'Time_Offset(s)', 'EEG_Value', 'Sleep_Stage'
        ]
    else:
        columns = [
            'Patient_ID', 'Record_ID', 'Epoch_Index', 'Epoch_Duration(s)',
            'EEG_Mean', 'EEG_Std', 'EEG_Min', 'EEG_Max', 'EEG_Median',
            'EEG_Q1', 'EEG_Q3', 'Sleep_Stage'
        ]

    df = pd.DataFrame(df_list, columns=columns)

    # 添加睡眠阶段标签
    stage_labels = {
        0: 'W',  # Wakefulness
        1: 'N1',  # NREM Stage 1
        2: 'N2',  # NREM Stage 2
        3: 'N3',  # NREM Stage 3 (Deep Sleep)
        4: 'REM',  # REM Sleep
        5: 'MOVE',  # Movement
        6: 'UNK'  # Unknown
    }
    df['Stage_Label'] = df['Sleep_Stage'].map(stage_labels)

    return df


# ============================== 主程序区域 ==============================
def main():
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 获取所有NPZ文件
    npz_files = glob.glob(os.path.join(NPZ_DIR, '*.npz'))
    print(f"找到 {len(npz_files)} 个NPZ文件需要转换")

    # 处理所有文件
    for file_idx, npz_file in enumerate(npz_files):
        try:
            print(f"正在处理文件 {file_idx + 1}/{len(npz_files)}: {os.path.basename(npz_file)}")

            # 转换文件
            df = convert_npz_to_csv(npz_file, SAVE_FULL_SEQUENCE)

            # 生成输出路径
            csv_filename = os.path.basename(npz_file).replace('.npz', '.csv')
            csv_path = os.path.join(OUTPUT_DIR, csv_filename)

            # 保存到CSV
            df.to_csv(csv_path, index=False)
            print(f"  -> 已保存到: {csv_path}")

        except Exception as e:
            print(f"处理文件出错: {os.path.basename(npz_file)}")
            print(f"错误信息: {str(e)}")

    print("\n转换完成!")
    print(f"共处理 {len(npz_files)} 个文件")
    print(f"输出目录: {OUTPUT_DIR}")
    if SAVE_FULL_SEQUENCE:
        print("模式: 完整时间序列 (文件较大)")
    else:
        print("模式: Epoch统计特征 (文件较小)")


if __name__ == '__main__':
    main()