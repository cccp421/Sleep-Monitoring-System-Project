import tensorflow as tf
from tensorflow.keras import layers, Model
import numpy as np


def focal_categorical_loss(alpha=[0.1, 0.3, 0.1, 0.2, 0.1], gamma=2.0):
    """Focal Loss替代原加权损失函数，增强对少样本类别的处理能力"""

    def loss(y_true, y_pred):
        # 计算交叉熵
        ce = -y_true * tf.math.log(tf.clip_by_value(y_pred, 1e-7, 1.0))

        # 计算概率调制因子
        p_t = tf.reduce_sum(y_true * y_pred, axis=-1)
        modulating_factor = tf.pow(1.0 - p_t, gamma)

        # 应用类别权重
        alpha_factor = tf.reduce_sum(alpha * y_true, axis=-1)

        # 组合Focal Loss
        focal_loss = modulating_factor * alpha_factor * ce
        return tf.reduce_mean(focal_loss, axis=-1)

    return loss


def resnet_se_block(inputs, num_filters, kernel_size, strides, ratio=8):
    """优化后的残差SE模块（适配地平线BPU）"""
    # 主路径
    x = layers.Conv1D(
        filters=num_filters,
        kernel_size=kernel_size,
        strides=strides,
        padding='same',
        kernel_initializer='he_normal'
    )(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)

    x = layers.Conv1D(
        filters=num_filters,
        kernel_size=kernel_size,
        strides=strides,
        padding='same',
        kernel_initializer='he_normal'
    )(x)
    x = layers.BatchNormalization()(x)

    # SE注意力模块（优化版）
    se = layers.GlobalAveragePooling1D()(x)
    se = layers.Reshape((1, num_filters))(se)  # 保持3D格式

    se = layers.Dense(
        units=num_filters // ratio,
        activation='relu',
        kernel_initializer='he_normal'
    )(se)
    se = layers.Dense(
        units=num_filters,
        activation='hard_sigmoid',  # 量化友好的激活函数
        kernel_initializer='he_normal'
    )(se)

    # 应用注意力权重
    x = layers.Multiply()([x, se])

    # 快捷路径 (确保维度匹配)
    if strides > 1 or inputs.shape[-1] != num_filters:
        x_skip = layers.Conv1D(
            filters=num_filters,
            kernel_size=1,
            strides=strides,
            padding='same',
            kernel_initializer='he_normal'
        )(inputs)
        x_skip = layers.BatchNormalization()(x_skip)
    else:
        x_skip = inputs

    # 合并路径
    x = layers.Add()([x, x_skip])
    return layers.ReLU()(x)


def create_optimized_model(Fs=100, n_classes=5, seq_length=15, summary=True):
    """优化后的模型架构（保留LSTM，适配地平线RDK X3）"""
    # 输入层（调整为NHWC格式）
    x_input = layers.Input(shape=(seq_length, Fs * 30, 1))

    # 第一残差块
    x = resnet_se_block(x_input, 32, 3, 1, ratio=8)
    x = layers.MaxPooling1D(pool_size=4, strides=4, padding='same')(x)

    # 第二残差块
    x = resnet_se_block(x, 64, 5, 1, ratio=8)
    x = layers.MaxPooling1D(pool_size=4, strides=4, padding='same')(x)

    # 第三残差块
    x = resnet_se_block(x, 128, 7, 1, ratio=8)

    # 调整维度并添加LSTM
    x = layers.Reshape((seq_length, -1))(x)  # 保持时间步维度
    x = layers.LSTM(
        units=64,
        dropout=0.5,
        activation='tanh',  # 使用tanh获得更好的量化性能
        return_sequences=True,
        recurrent_activation='hard_sigmoid'  # 量化友好的激活函数
    )(x)

    # 输出层适配（满足BPU的Softmax约束）
    x = layers.Dense(n_classes, activation='linear')(x)  # 不加softmax
    x = layers.Reshape((seq_length, 1, n_classes))(x)  # [seq_len, 1, n_classes]
    x = layers.Permute((3, 1, 2))(x)  # [n_classes, seq_len, 1]
    x_out = layers.Softmax(axis=1)(x)  # 满足axis=1的四维输入

    # 模型编译
    model = Model(inputs=x_input, outputs=x_out)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss=focal_categorical_loss(),
        metrics=['accuracy']
    )

    if summary:
        model.summary()
        try:
            tf.keras.utils.plot_model(
                model, to_file='optimized_model.png',
                show_shapes=True, dpi=300, expand_nested=True
            )
        except:
            print("Graphviz not installed, skipping model plot")

    return model


# 创建模型实例
model = create_optimized_model(summary=True)