import tensorflow as tf


def create_LSTM_model(input_shape=(3000, 3)):  # 修改输入维度为3
    """优化后的睡眠阶段分类模型（适配3通道输入）"""
    model = tf.keras.Sequential([
        # 输入层（维度更新）
        tf.keras.layers.InputLayer(input_shape=input_shape),

        # 并行多尺度卷积
        tf.keras.layers.Conv1D(16, 15, strides=2, activation='swish', padding='same'),
        tf.keras.layers.BatchNormalization(),

        # 时序特征提取（保持双向LSTM结构）
        tf.keras.layers.Bidirectional(
            tf.keras.layers.LSTM(32, return_sequences=True),
            merge_mode='concat'
        ),
        tf.keras.layers.Dropout(0.2),

        # 深度特征提取（保持可分离卷积）
        tf.keras.layers.SeparableConv1D(64, 5, padding='same'),
        tf.keras.layers.ReLU(threshold=0.3),
        tf.keras.layers.MaxPooling1D(2),

        # 输出层（维度保持不变）
        tf.keras.layers.GlobalAvgPool1D(),
        tf.keras.layers.Dense(32, activation='swish',
                              kernel_regularizer=tf.keras.regularizers.l1_l2(1e-4, 1e-3)),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(5, activation='softmax')
    ])
    return model


def create_embedded_model(input_shape=(3000, 3)):  # 修改输入维度为3
    """轻量级嵌入模型（适配3通道）"""
    model = tf.keras.Sequential([
        tf.keras.layers.InputLayer(input_shape=input_shape),

        # 卷积结构调整
        tf.keras.layers.Conv1D(8, 15, strides=3, activation='relu'),
        tf.keras.layers.DepthwiseConv1D(5, padding='same'),
        tf.keras.layers.ReLU(max_value=6.0),

        tf.keras.layers.GlobalAvgPool1D(),
        tf.keras.layers.Dense(5, activation='softmax')
    ])
    return model


def create_simple_model(input_shape=(3000, 3)):  # 修改输入维度为3
    """基础模型（适配3通道输入）"""
    model = tf.keras.Sequential([
        # 输入卷积层（调整kernel尺寸）
        tf.keras.layers.Conv1D(16, 30, strides=10, activation='relu',
                               input_shape=input_shape),
        tf.keras.layers.MaxPooling1D(3),

        # 特征提取层（保持结构）
        tf.keras.layers.Conv1D(32, 5, activation='relu'),
        tf.keras.layers.GlobalAvgPool1D(),

        # 输出层
        tf.keras.layers.Dense(5, activation='softmax')
    ])
    return model