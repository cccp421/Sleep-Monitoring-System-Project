import os
import pandas as pd
import numpy as np
from tqdm import tqdm
import re  # 新增正则表达式库

# 配置参数
INPUT_DIR = "E:/DREAMT base/DREAMT-main/data_100Hz"  # 原始数据目录
OUTPUT_DIR = "E:/DREAMT base/DREAMT-main/data_100Hz_processed"  # 处理结果目录
REQUIRED_COLS = [  # 需要保留的字段
    'TIMESTAMP',
    'ACC_X', 'ACC_Y', 'ACC_Z',
    'TEMP',
    'HR',
    'SAO2',
    # 'ECG',
    'Sleep_Stage'
]

# 创建输出目录
os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_participant_id(filename):
    """使用正则表达式从文件名提取参与者编号 (如 S002/S012)"""
    match = re.search(r'S(\d{3})', filename)
    if match:
        return f"S{match.group(1)}"
    raise ValueError(f"文件名 {filename} 中未找到参与者编号")

def process_sleep_stage_all(df):
    """处理睡眠阶段标签（保留N1/N2/N3独立状态，清除P）"""
    allowed_stages = ['W', 'N1', 'N2', 'N3', 'R']  # 定义允许保留的状态
    df = df[df['Sleep_Stage'].isin(allowed_stages)]  # 过滤无效状态（如P）
    return df


def clean_data(df):
    """执行数据清洗操作"""
    # 处理无穷值
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # 删除高缺失值特征（列缺失超过2000条）
    missing_counts = df.isna().sum()
    columns_to_drop = missing_counts[missing_counts > 2000].index
    df = df.drop(columns=columns_to_drop)

    # 删除包含任何NaN的行
    df = df.dropna(axis=0, how='any')

    return df

def process_file(input_path, output_filename):
    """处理单个数据文件"""
    try:
        df = pd.read_csv(input_path, usecols=REQUIRED_COLS)
        # df = process_sleep_stage(df)
        df = process_sleep_stage_all(df)
        df = clean_data(df)
        if df.empty:
            print(f"警告：文件 {input_path} 处理后无有效数据")
            return False
        df.to_csv(output_filename, index=False)
        return True
    except Exception as e:
        print(f"处理文件 {input_path} 出错: {str(e)}")
        return False


# 获取待处理文件列表
file_list = [f for f in os.listdir(INPUT_DIR) if f.endswith('.csv')]
print(f"发现 {len(file_list)} 个数据文件需要处理")

# 批量处理文件
success_count = 0
for filename in tqdm(file_list, desc="处理进度"):
    try:
        # 生成新文件名
        participant_id = extract_participant_id(filename)
        output_filename = os.path.join(OUTPUT_DIR, f"{participant_id}_PSG_df_updated.csv")

        # 处理文件
        input_path = os.path.join(INPUT_DIR, filename)
        if process_file(input_path, output_filename):
            success_count += 1
    except Exception as e:
        print(f"文件 {filename} 处理失败: {str(e)}")

# 输出统计
print(f"\n处理完成！成功处理 {success_count}/{len(file_list)} 个文件")
print(f"处理后文件示例: {os.listdir(OUTPUT_DIR)[:3]}")  # 显示前3个输出文件