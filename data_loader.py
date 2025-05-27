import numpy as np
import pandas as pd
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import tensorflow as tf


def load_and_process(csv_path):
    """加载单个CSV文件并进行窗口化处理（特征维度减少为3）"""
    df = pd.read_csv(csv_path)

    # 确保数据足够生成至少一个窗口
    window_size = 3000
    min_samples = window_size
    if len(df) < min_samples:
        return np.array([]), np.array([])

    # 更新特征列（移除ACC相关）
    features = df[['TEMP', 'HR', 'SAO2']].values.astype(np.float32)

    # 标签映射保持不变
    stage_mapping = {'W': 0, 'N1': 1, 'N2': 2, 'N3': 3, 'R': 4}
    labels = df['Sleep_Stage'].map(stage_mapping).values

    if np.isnan(labels).any():
        raise ValueError("数据中包含未定义的睡眠阶段标签")

    X, y = [], []
    for i in range(0, len(features) - window_size + 1, window_size // 2):
        window = features[i:i + window_size]
        window_labels = labels[i:i + window_size]

        augmented = augment_window(window)
        if augmented.shape[0] != window_size:
            augmented = augmented[:window_size]

        label_counts = np.bincount(window_labels, minlength=5)
        most_common_label = np.argmax(label_counts)

        X.append(augmented)
        y.append(most_common_label)

    return np.array(X), np.array(y)


def prepare_datasets(data_dir, save_path):
    """处理数据集（特征维度调整为3）"""
    all_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.csv')]
    train_files, test_files = train_test_split(all_files, test_size=0.2, random_state=42)

    # 标准化参数计算（特征维度3）
    print("正在计算标准化参数...")
    all_train_features = []
    for f in train_files:
        X, _ = load_and_process(f)
        if X.size > 0:
            all_train_features.append(X.reshape(-1, 3))  # 修改reshape维度
    scaler = StandardScaler().fit(np.concatenate(all_train_features))

    def process_files(files):
        all_X, all_y = [], []
        for f in files:
            X, y = load_and_process(f)
            if X.size > 0:
                # 标准化并保持新维度
                X = scaler.transform(X.reshape(-1, 3)).reshape(X.shape)
                all_X.append(X)
                all_y.append(y)
        return np.concatenate(all_X), np.concatenate(all_y)

    print("正在处理训练集...")
    X_train, y_train = process_files(train_files)
    print("正在处理测试集...")
    X_test, y_test = process_files(test_files)

    np.savez_compressed(
        save_path,
        X_train=X_train, y_train=y_train,
        X_test=X_test, y_test=y_test
    )
    joblib.dump(scaler, save_path.replace('.npz', '_scaler.pkl'))
    return (X_train, y_train), (X_test, y_test)


def augment_window(window):
    """数据增强（特征维度调整为3）"""
    original_length = window.shape[0]
    window_aug = window.copy()

    # 时间扭曲增强
    if np.random.rand() > 0.5:
        warp_factor = np.random.uniform(0.8, 1.2)
        new_length = int(original_length * warp_factor)

        x_orig = np.arange(original_length)
        x_new = np.linspace(0, original_length - 1, new_length)

        # 调整特征维度为3
        warped = np.zeros((new_length, 3))
        for col in range(3):  # 循环次数改为3
            warped[:, col] = np.interp(x_new, x_orig, window[:, col])

        if new_length >= original_length:
            window_aug = warped[:original_length]
        else:
            padding = np.zeros((original_length - new_length, 3))  # 填充维度改为3
            window_aug = np.vstack([warped, padding])

    # 噪声添加保持不变
    noise = np.random.normal(0, 0.05, size=window_aug.shape)
    return window_aug + noise


# 以下函数保持不变，但会反映新特征维度
def load_prepared_data(save_path):
    """加载已处理的数据"""
    data = np.load(save_path)
    scaler = joblib.load(save_path.replace('.npz', '_scaler.pkl'))
    return (
        (data['X_train'], data['y_train']),
        (data['X_test'], data['y_test']),
        scaler
    )


def check_class_distribution(y):
    """类别分布检查（保持不变）"""
    class_counts = np.bincount(y, minlength=5)
    print("\n类别分布:")
    print(
        f"W: {class_counts[0]}\nN1: {class_counts[1]}\nN2: {class_counts[2]}\nN3: {class_counts[3]}\nR: {class_counts[4]}")
    print(f"类别权重建议: {len(y) / (5 * class_counts + 1e-7)}")


def data_diagnosis(X, y):
    """数据质量诊断（自动适应新维度）"""
    print(f"包含NaN的样本数: {np.isnan(X).any(axis=(1, 2)).sum()}")

    class_counts = np.bincount(y, minlength=5)
    print("类别分布:")
    print(
        f"W: {class_counts[0]} | N1: {class_counts[1]} | N2: {class_counts[2]} | N3: {class_counts[3]} | R: {class_counts[4]}")

    print("特征统计:")
    print(f"均值={X.mean(axis=(0, 1))}")
    print(f"标准差={X.std(axis=(0, 1))}")