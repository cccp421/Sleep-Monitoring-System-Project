import argparse
import numpy as np
import tensorflow as tf
from tensorflow.keras import backend as K
from tensorflow.keras.models import load_model


# 1. 重新定义模型所需的函数和结构
def weighted_categorical_crossentropy(weights):
    weights = tf.Variable(weights, dtype=tf.float32)

    def loss(y_true, y_pred):
        # 缩放预测值，使每个样本的类别概率总和为1
        y_pred /= tf.reduce_sum(y_pred, axis=-1, keepdims=True)

        # 裁剪以防止NaN和Inf
        y_pred = tf.clip_by_value(y_pred, 1e-7, 1 - 1e-7)

        # 计算加权损失
        loss_val = y_true * tf.math.log(y_pred) * weights
        loss_val = -tf.reduce_sum(loss_val, axis=-1)
        return loss_val

    return loss


def resnet_se_block(inputs, num_filters, kernel_size, strides, ratio):
    # 1D卷积
    x = tf.keras.layers.Conv1D(filters=num_filters, kernel_size=kernel_size,
                               strides=strides, padding='same',
                               kernel_initializer='he_normal')(inputs)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation('relu')(x)
    x = tf.keras.layers.Conv1D(filters=num_filters, kernel_size=kernel_size,
                               strides=strides, padding='same',
                               kernel_initializer='he_normal')(x)
    x = tf.keras.layers.BatchNormalization()(x)

    # SE块 - 使用TF内置函数代替K.mean
    se = tf.keras.layers.Lambda(
        lambda x: tf.reduce_mean(x, axis=-2, keepdims=True)
    )(x)
    se = tf.keras.layers.Dense(units=num_filters // ratio)(se)
    se = tf.keras.layers.Activation('relu')(se)
    se = tf.keras.layers.Dense(units=num_filters)(se)
    se = tf.keras.layers.Activation('sigmoid')(se)
    x = tf.keras.layers.multiply([x, se])

    # 跳跃连接
    x_skip = tf.keras.layers.Conv1D(filters=num_filters, kernel_size=1,
                                    strides=1, padding='same',
                                    kernel_initializer='he_normal')(inputs)
    x_skip = tf.keras.layers.BatchNormalization()(x_skip)

    x = tf.keras.layers.Add()([x, x_skip])
    x = tf.keras.layers.Activation('relu')(x)
    return x


def create_model(Fs=100, n_classes=5, seq_length=15, summary=False):
    # 注意：输入形状调整为 (seq_length, 3000, 1)
    x_input = tf.keras.Input(shape=(seq_length, 30 * Fs, 1))

    x = resnet_se_block(x_input, 32, 3, 1, 4)
    x = tf.keras.layers.MaxPool2D(pool_size=(4, 1), strides=(4, 1),
                                  padding='same', data_format='channels_last')(x)

    x = resnet_se_block(x, 64, 5, 1, 4)
    x = tf.keras.layers.MaxPool2D(pool_size=(4, 1), strides=(4, 1),
                                  padding='same', data_format='channels_last')(x)

    x = resnet_se_block(x, 128, 7, 1, 4)
    # 使用TF内置函数代替K.mean
    x = tf.keras.layers.Lambda(
        lambda x: tf.reduce_mean(x, axis=-2, keepdims=False)
    )(x)

    x = tf.keras.layers.Dropout(rate=0.5)(x)

    # LSTM
    x = tf.keras.layers.LSTM(units=64, dropout=0.5,
                             activation='relu', return_sequences=True)(x)

    # 分类
    x_out = tf.keras.layers.Dense(units=n_classes, activation='softmax')(x)

    model = tf.keras.models.Model(x_input, x_out)
    return model


# 2. 加载模型的权重而不是整个模型
def load_model_with_weights(model_path):
    # 先创建一个新模型实例
    model = create_model(seq_length=15)

    # 加载权重
    model.load_weights(model_path)
    return model


# 3. 数据准备和推理函数
def prepare_inference_data(npz_path, seq_length=15):
    """准备推理数据"""
    data = np.load(npz_path)
    x = data["x"]

    # 序列化处理
    sequences = []
    start_index = 0
    while start_index + seq_length <= len(x):
        seq = x[start_index:start_index + seq_length]
        sequences.append(seq)
        start_index += seq_length

    x_seq = np.array(sequences)
    x_seq = np.expand_dims(x_seq, axis=-1)  # 添加通道维度
    return x_seq


def run_inference(model, input_data):
    """运行模型推理"""
    return model.predict(input_data)


# 4. 主函数
def main():
    # 解析参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", type=str, default="model.h5",
                        help="Path to saved model")
    parser.add_argument("--data_path", type=str,
                        default="E:/DREAMT base/sleep-edf/sleep-edf-database-expanded-1.0.0/sleep-cassette/eeg_fpz_cz/SC4032E0.npz",
                        help="Path to test NPZ file")
    args = parser.parse_args()

    # 创建模型并加载权重
    model = load_model_with_weights(args.model_path)

    # 准备数据
    X_inference = prepare_inference_data(args.data_path)

    # 运行推理
    predictions = run_inference(model, X_inference)

    # 处理预测结果
    all_preds = []
    for seq in predictions:
        epoch_preds = np.argmax(seq, axis=-1)
        all_preds.extend(epoch_preds.tolist())

    # 睡眠阶段映射
    stage_map = {0: "Wake", 1: "N1", 2: "N2", 3: "N3", 4: "REM"}
    sleep_stages = [stage_map[p] for p in all_preds]

    print("\n睡眠阶段预测结果:")
    for i, stage in enumerate(sleep_stages[:]):  # 只打印前20个作为示例
        print(f"Epoch {i + 1}: {stage}")

    print(f"\n共预测了 {len(sleep_stages)} 个epoch")


if __name__ == "__main__":
    main()