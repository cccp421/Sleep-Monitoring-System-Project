import tensorflow as tf
import numpy as np
import os
from sklearn.utils import class_weight
from data_loader import load_prepared_data, data_diagnosis
from model import create_LSTM_model, create_embedded_model, create_simple_model

def main():
    # 配置路径
    RAW_DATA_DIR = "E:/DREAMT base/DREAMT-main/data_100Hz_processed"
    PROCESSED_PATH = "E:/DREAMT base/DREAMT-main/data_100Hz_processed/processed_data.npz"

    # 自动数据预处理
    if not os.path.exists(PROCESSED_PATH):
        print("首次运行，正在处理数据...")
        from data_loader import prepare_datasets
        (X_train, y_train), (X_val, y_val), (X_test, y_test) = prepare_datasets(RAW_DATA_DIR, PROCESSED_PATH)
    else:
        print("加载已处理数据...")
        (X_train, y_train), (X_val, y_val), (X_test, y_test), scaler = load_prepared_data(PROCESSED_PATH)

    # 数据质量诊断
    data_diagnosis(X_train, y_train)
    data_diagnosis(X_val, y_val)

    # 验证数据形状
    print(f"\n训练集形状: X{X_train.shape} y{y_train.shape}")
    print(f"验证集形状: X{X_val.shape} y{y_val.shape}")

    # 计算并整合类别权重
    classes = np.unique(y_train)
    class_weights = class_weight.compute_class_weight(
        'balanced',
        classes=classes,
        y=y_train
    )
    print(f"\n类别权重数组: {class_weights} (顺序对应类别0-4)")

    # 将权重转换为Tensor张量
    class_weights_tensor = tf.constant(class_weights, dtype=tf.float32)

    # 优化后的模型配置
    # model = create_LSTM_model(input_shape=(3000, 6))
    # model = create_embedded_model(input_shape=(3000, 6))
    model = create_simple_model(input_shape=(3000, 6))

    # 优化器
    optimizer = tf.keras.optimizers.Adam(
        learning_rate=1e-3,
        # 保持类似AdamW的配置
        beta_1=0.9,
        beta_2=0.999,
        epsilon=1e-7
    )

    # 综合Focal Loss和类别权重的自定义损失函数
    def focal_loss(gamma=2):
        """
        整合类别权重的Focal Loss
        参数说明：
        建议首次运行时保持gamma=2的参数设置，后续可根据训练日志调整：
        如果验证损失震荡：尝试gamma=1.5
        如果收敛速度慢：尝试gamma=2.5
        如果类别0和2的准确率仍低：适当提高对应权重系数
        """
        def _loss(y_true, y_pred):
            # 计算基础交叉熵损失
            ce_loss = tf.keras.losses.sparse_categorical_crossentropy(y_true, y_pred)

            # 计算概率和焦点因子
            probs = tf.math.exp(-ce_loss)
            focal_factor = tf.pow(1.0 - probs, gamma)

            # 获取类别权重
            weights = tf.gather(class_weights_tensor, tf.cast(y_true, tf.int32))

            # 组合加权损失
            return weights * focal_factor * ce_loss

        return _loss

    # 模型编译
    model.compile(
        optimizer=optimizer,
        loss=focal_loss(gamma=2),  # 使用gamma=2
        metrics=['accuracy',
                 tf.keras.metrics.SparseTopKCategoricalAccuracy(k=2, name='top2_accuracy')]
    )

    # 增强的回调设置
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_top2_accuracy',
            patience=100,
            mode='max',
            restore_best_weights=True
        ),
        tf.keras.callbacks.ModelCheckpoint(
            'best_model.h5',
            monitor='val_top2_accuracy',
            save_best_only=True,
            mode='max'
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_top2_accuracy',
            factor=0.5,
            patience=5,
            mode='max'
        ),
        tf.keras.callbacks.CSVLogger('training_log.csv')
    ]

    # 训练参数设置
    print("\n[开始训练]")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=200,
        batch_size=64,
        callbacks=callbacks,  # 移除了class_weight参数
        verbose=1,
        shuffle=True
    )

    # 训练后分析
    print("\n[训练完成] 最佳模型已保存为 best_model.h5")
    print("验证集最终指标:")
    model.evaluate(X_val, y_val, verbose=2)


if __name__ == "__main__":
    main()