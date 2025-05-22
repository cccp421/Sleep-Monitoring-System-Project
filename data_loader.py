import numpy as np
import pandas as pd
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import tensorflow as tf


def load_and_process(csv_path):
    """加载单个CSV文件并进行窗口化处理（不标准化）"""
    df = pd.read_csv(csv_path)

    # 确保数据足够生成至少一个窗口
    window_size = 3000
    min_samples = window_size
    if len(df) < min_samples:
        return np.array([]), np.array([])  # 跳过不足的数据

    features = df[['ACC_X', 'ACC_Y', 'ACC_Z', 'TEMP', 'HR', 'SAO2']].values.astype(np.float32)

    # 标签映射为3个类别
    # labels = df['Sleep_Stage'].map({'W': 0, 'N': 1, 'R': 2}).values

    # 更新标签映射为5个类别
    stage_mapping = {'W': 0, 'N1': 1, 'N2': 2, 'N3': 3, 'R': 4}
    labels = df['Sleep_Stage'].map(stage_mapping).values

    # 检查是否有未映射的标签
    if np.isnan(labels).any():
        raise ValueError("数据中包含未定义的睡眠阶段标签")

    X, y = [], []
    for i in range(0, len(features) - window_size + 1, window_size // 2):
        window = features[i:i + window_size]
        window_labels = labels[i:i + window_size]

        # 数据增强
        augmented = augment_window(window)

        # 确保长度为3000
        if augmented.shape[0] != window_size:
            augmented = augmented[:window_size]

        # 取标签众数（使用bincount的minlength确保维度）
        label_counts = np.bincount(window_labels, minlength=5)
        most_common_label = np.argmax(label_counts)

        X.append(augmented)
        y.append(most_common_label)

    return np.array(X), np.array(y)


def prepare_datasets(data_dir, save_path):
    """处理数据集并保存为单个文件"""
    # 获取所有CSV文件
    all_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.csv')]

    # 按受试者划分数据集
    train_files, temp_files = train_test_split(all_files, test_size=0.2, random_state=42)
    val_files, test_files = train_test_split(temp_files, test_size=0.5, random_state=42)

    # 计算标准化参数
    print("正在计算标准化参数...")
    all_train_features = []
    for f in train_files:
        X, _ = load_and_process(f)
        all_train_features.append(X.reshape(-1, 6))
    scaler = StandardScaler().fit(np.concatenate(all_train_features))

    # 封装处理函数
    def process_files(files):
        all_X, all_y = [], []
        for f in files:
            X, y = load_and_process(f)
            X = scaler.transform(X.reshape(-1, 6)).reshape(X.shape)
            all_X.append(X)
            all_y.append(y)
        return np.concatenate(all_X), np.concatenate(all_y)

    # 处理各数据集
    print("正在处理训练集...")
    X_train, y_train = process_files(train_files)
    print("正在处理验证集...")
    X_val, y_val = process_files(val_files)
    print("正在处理测试集...")
    X_test, y_test = process_files(test_files)

    # 保存所有数据
    np.savez_compressed(
        save_path,
        X_train=X_train, y_train=y_train,
        X_val=X_val, y_val=y_val,
        X_test=X_test, y_test=y_test
    )
    joblib.dump(scaler, save_path.replace('.npz', '_scaler.pkl'))
    return (X_train, y_train), (X_val, y_val), (X_test, y_test)


def load_prepared_data(save_path):
    """加载已处理的数据"""
    data = np.load(save_path)
    scaler = joblib.load(save_path.replace('.npz', '_scaler.pkl'))
    return (
        (data['X_train'], data['y_train']),
        (data['X_val'], data['y_val']),
        (data['X_test'], data['y_test']),
        scaler
    )


def check_class_distribution(y):
    """数据权重分布（支持5个类别）"""
    class_counts = np.bincount(y, minlength=5)
    print("\n类别分布:")
    print(
        f"W: {class_counts[0]}\nN1: {class_counts[1]}\nN2: {class_counts[2]}\nN3: {class_counts[3]}\nR: {class_counts[4]}")
    print(f"类别权重建议: {len(y) / (5 * class_counts + 1e-7)}")  # 添加微小值防止除零


def data_diagnosis(X, y):
    """数据质量诊断（支持5个类别）"""
    # 检查NaN值
    print(f"包含NaN的样本数: {np.isnan(X).any(axis=(1, 2)).sum()}")

    # 检查标签分布
    class_counts = np.bincount(y, minlength=5)
    print("类别分布:")
    print(
        f"W: {class_counts[0]} | N1: {class_counts[1]} | N2: {class_counts[2]} | N3: {class_counts[3]} | R: {class_counts[4]}")

    # 检查特征范围
    print("特征统计:")
    print(f"均值={X.mean(axis=(0, 1))}")
    print(f"标准差={X.std(axis=(0, 1))}")


def augment_window(window):
    """数据增强，保持窗口长度为3000"""
    original_length = window.shape[0]
    window_aug = window.copy()

    # 随机时间扭曲
    if np.random.rand() > 0.5:
        warp_factor = np.random.uniform(0.8, 1.2)
        new_length = int(original_length * warp_factor)

        # 生成插值后的时间序列
        x_orig = np.arange(original_length)
        x_new = np.linspace(0, original_length - 1, new_length)

        # 对每个特征通道进行插值
        warped = np.zeros((new_length, 6))
        for col in range(6):
            warped[:, col] = np.interp(x_new, x_orig, window[:, col])

        # 截断或填充回原始长度
        if new_length >= original_length:
            window_aug = warped[:original_length]
        else:
            padding = np.zeros((original_length - new_length, 6))
            window_aug = np.vstack([warped, padding])

    # 添加高斯噪声
    noise = np.random.normal(0, 0.05, size=window_aug.shape)
    return window_aug + noise