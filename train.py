import tensorflow as tf
import numpy as np
import os
from sklearn.utils import class_weight
from data_loader import load_prepared_data, data_diagnosis
from model import create_LSTM_model, create_embedded_model, create_simple_model
import joblib

def main():
    # 配置路径
    RAW_DATA_DIR = "E:/DREAMT base/DREAMT-main/data_100Hz_processed"
    PROCESSED_PATH = "E:/DREAMT base/DREAMT-main/data_100Hz_processed/processed_data.npz"

    # 自动数据预处理
    if not os.path.exists(PROCESSED_PATH):
        print("首次运行，正在处理数据...")
        from data_loader import prepare_datasets
        # 直接获取训练集和测试集（测试集将作为验证集）
        (X_train, y_train), (X_test, y_test) = prepare_datasets(RAW_DATA_DIR, PROCESSED_PATH)
        scaler = joblib.load(PROCESSED_PATH.replace('.npz', '_scaler.pkl'))
    else:
        print("加载已处理数据...")
        # 加载两个数据集和标准化器
        (X_train, y_train), (X_test, y_test), scaler = load_prepared_data(PROCESSED_PATH)

    # 数据质量诊断
    print("\n训练集诊断:")
    data_diagnosis(X_train, y_train)
    print("\n验证集/测试集诊断:")
    data_diagnosis(X_test, y_test)

    # 验证数据形状
    print(f"\n训练集形状: X{X_train.shape} y{y_train.shape}")
    print(f"验证集/测试集形状: X{X_test.shape} y{y_test.shape}")

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

    # 模型配置（保持原有选择）
    model = create_simple_model(input_shape=(3000, 6))

    # 优化器配置
    optimizer = tf.keras.optimizers.Adam(
        learning_rate=1e-3,
        beta_1=0.9,
        beta_2=0.999,
        epsilon=1e-7
    )

    # Focal Loss定义（保持原有实现）
    def focal_loss(gamma=2):
        def _loss(y_true, y_pred):
            ce_loss = tf.keras.losses.sparse_categorical_crossentropy(y_true, y_pred)
            probs = tf.math.exp(-ce_loss)
            focal_factor = tf.pow(1.0 - probs, gamma)
            weights = tf.gather(class_weights_tensor, tf.cast(y_true, tf.int32))
            return weights * focal_factor * ce_loss
        return _loss

    # 模型编译
    model.compile(
        optimizer=optimizer,
        loss=focal_loss(gamma=2),
        metrics=['accuracy']
    )

    # 回调配置（直接监控测试集）
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_accuracy',
            patience=50,
            mode='max',
            restore_best_weights=True
        ),
        tf.keras.callbacks.ModelCheckpoint(
            'best_model.h5',
            monitor='val_accuracy',
            save_best_only=True,
            mode='max'
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_accuracy',
            factor=0.5,
            patience=5,
            mode='max'
        ),
        tf.keras.callbacks.CSVLogger('training_log.csv')
    ]

    # 训练参数设置（使用测试集作为验证）
    print("\n[开始训练]")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),  # 直接使用测试集作为验证
        epochs=200,
        batch_size=64,
        callbacks=callbacks,
        verbose=1,
        shuffle=True
    )

    # 最终评估
    print("\n[训练完成] 最佳模型已保存为 best_model.h5")
    print("最终测试集评估结果:")
    model.evaluate(X_test, y_test, verbose=2)

if __name__ == "__main__":
    main()