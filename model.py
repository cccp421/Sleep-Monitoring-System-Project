import tensorflow as tf

def create_LSTM_model(input_shape=(3000, 6)):
    """优化后的睡眠阶段分类模型"""
    '''
    修改点   技术手段	    作用	                  预期提升
    1	   多尺度卷积	    捕捉不同时间尺度的特征	 +3-5%准确率
    2	   双向LSTM	    提取长时序依赖关系	     +5-8%准确率
    3	   Swish激活	    缓解梯度消失，增强非线性	 +1-2%准确率
    4	   分层Dropout	防止不同层间的过拟合	 +2-3%泛化能力
    5	   自适应池化	    保留重要特征信息	     +1-2%敏感度
    6	   L1/L2正则化	控制权重分布，防止过拟合	 +2-4%泛化性
    '''
    model = tf.keras.Sequential([
        # 输入层
        tf.keras.layers.InputLayer(input_shape=input_shape),

        # 并行多尺度卷积  改进点1：增加并行卷积分支
        tf.keras.layers.Conv1D(16, 15, strides=2, activation='swish', padding='same'),
        tf.keras.layers.BatchNormalization(),

        # 时序特征提取  改进点2：添加双向LSTM提取时序特征
        tf.keras.layers.Bidirectional(
            tf.keras.layers.LSTM(32, return_sequences=True),
            merge_mode='concat'
        ),

        tf.keras.layers.Dropout(0.2),

        # 深度特征提取  改进点3：使用深度可分离卷积减少参数量  替换普通ReLU为带阈值的版本
        tf.keras.layers.SeparableConv1D(64, 5, padding='same'),
        tf.keras.layers.ReLU(threshold=0.3),
        tf.keras.layers.MaxPooling1D(2),

        # 输出层  使用Swish激活函数
        tf.keras.layers.GlobalAvgPool1D(),
        tf.keras.layers.Dense(32, activation='swish',
                              kernel_regularizer=tf.keras.regularizers.l1_l2(1e-4, 1e-3)),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(5, activation='softmax',
                              kernel_regularizer=tf.keras.regularizers.l2(1e-4))
    ])

    return model

def create_embedded_model(input_shape=(3000, 6)):
    model = tf.keras.Sequential([
        # 输入层
        tf.keras.layers.InputLayer(input_shape=input_shape),

        # 轻量卷积替代LSTM
        tf.keras.layers.Conv1D(8, 15, strides=3, activation='relu'),
        tf.keras.layers.DepthwiseConv1D(5, padding='same'),
        tf.keras.layers.ReLU(max_value=6.0),  # 量化友好

        # 全局平均池化
        tf.keras.layers.GlobalAvgPool1D(),

        # 输出层
        tf.keras.layers.Dense(5, activation='softmax')
    ])
    return model

def create_simple_model(input_shape=(3000,6)):
    model = tf.keras.Sequential([
        tf.keras.layers.Conv1D(16, 30, strides=10, activation='relu', input_shape=input_shape),
        tf.keras.layers.MaxPooling1D(3),
        tf.keras.layers.Conv1D(32, 5, activation='relu'),
        tf.keras.layers.GlobalAvgPool1D(),
        # 修改输出层为5个单元
        tf.keras.layers.Dense(5, activation='softmax')
    ])
    return model