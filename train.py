# train.py 修改内容
import tensorflow as tf
import numpy as np
import os
from sklearn.utils import class_weight
from data_loader import generate_kfold_splits, prepare_single_fold, data_diagnosis, create_experiment_dir
from model import create_simple_model

def main():
    # 配置路径
    RAW_DATA_DIR = "E:/DREAMT base/DREAMT-main/data_100Hz_processed"
    N_FOLDS = 5

    # 创建版本化目录
    exp_dir = create_experiment_dir()
    print(f"\n实验版本目录: {exp_dir}")

    # 获取所有文件路径
    all_files = [os.path.join(RAW_DATA_DIR, f)
                 for f in os.listdir(RAW_DATA_DIR) if f.endswith('.csv')]

    # 生成K折划分
    kfold_splits = generate_kfold_splits(RAW_DATA_DIR, N_FOLDS)

    # 存储各fold结果
    fold_results = []

    for fold_idx, (train_idx, val_idx) in enumerate(kfold_splits):
        print(f"\n=== Processing Fold {fold_idx + 1}/{N_FOLDS} ===")
        # 创建fold专用目录
        fold_dir = exp_dir / f"fold_{fold_idx + 1}"
        fold_dir.mkdir()

        # 获取当前fold的文件列表
        train_files = [all_files[i] for i in train_idx]
        val_files = [all_files[i] for i in val_idx]

        # 处理数据
        X_train, y_train, X_val, y_val, scaler = prepare_single_fold(train_files, val_files)

        # 数据检查
        print(f"\n训练集样本数: {len(X_train)}")
        print(f"验证集样本数: {len(X_val)}")
        data_diagnosis(X_train, y_train)

        # 处理类别不平衡
        classes = np.unique(y_train)
        class_weights = class_weight.compute_class_weight(
            'balanced', classes=classes, y=y_train)
        class_weights_dict = {i: w for i, w in enumerate(class_weights)}

        # 创建模型
        model = create_simple_model(input_shape=(3000, 3))

        # 定义当前fold的focal loss
        class_weights_tensor = tf.constant(class_weights, dtype=tf.float32)

        def focal_loss(y_true, y_pred):
            gamma = 2
            ce_loss = tf.keras.losses.sparse_categorical_crossentropy(y_true, y_pred)
            probs = tf.math.exp(-ce_loss)
            focal_factor = tf.pow(1.0 - probs, gamma)
            weights = tf.gather(class_weights_tensor, tf.cast(y_true, tf.int32))
            return tf.reduce_mean(weights * focal_factor * ce_loss)

        # 编译模型
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
            loss=focal_loss,
            metrics=['accuracy'],
        )

        # 回调函数
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_accuracy', patience=20, restore_best_weights=True),
            tf.keras.callbacks.ModelCheckpoint(
                str(fold_dir / 'best_model.h5'), save_best_only=True),
            tf.keras.callbacks.CSVLogger(str(fold_dir / 'training_log.csv'))
        ]

        # 训练
        history = model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=100,
            batch_size=32,
            callbacks=callbacks,
            class_weight=class_weights_dict,
            verbose=1
        )

        # 记录结果
        val_acc = max(history.history['val_accuracy'])
        fold_results.append(val_acc)
        print(f"Fold {fold_idx + 1} 最佳验证准确率: {val_acc:.4f}")

    # 输出最终结果
    print("\n=== 交叉验证结果 ===")
    print(f"各fold验证准确率: {fold_results}")
    print(f"平均验证准确率: {np.mean(fold_results):.4f} ± {np.std(fold_results):.4f}")


if __name__ == "__main__":
    main()