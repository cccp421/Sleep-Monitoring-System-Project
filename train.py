import tensorflow as tf
from tensorflow.keras import metrics
print("TensorFlow Version:", tf.__version__)
import numpy as np
import os
import gc
from sklearn.utils import class_weight
from data_loader import generate_kfold_splits, prepare_single_fold, data_diagnosis, create_experiment_dir
from model import create_simple_model
from sklearn.metrics import classification_report, confusion_matrix
import pandas as pd
import matplotlib.pyplot as plt

class MacroPrecision(metrics.Metric):
    def __init__(self, name='macro_precision', **kwargs):
        super().__init__(name=name, **kwargs)
        self.precisions = [
            metrics.Precision(class_id=i)
            for i in range(5)  # 假设有5个类别
        ]

    def update_state(self, y_true, y_pred, sample_weight=None):
        y_pred = tf.argmax(y_pred, axis=1)
        for i in range(5):
            self.precisions[i].update_state(
                tf.cast(y_true == i, tf.float32),
                tf.cast(y_pred == i, tf.float32),
                sample_weight
            )

    def result(self):
        return tf.reduce_mean([p.result() for p in self.precisions])

    def reset_state(self):
        for p in self.precisions:
            p.reset_state()

class MacroRecall(metrics.Metric):
    def __init__(self, name='macro_recall', **kwargs):
        super().__init__(name=name, **kwargs)
        self.recalls = [
            metrics.Recall(class_id=i)
            for i in range(5)  # 假设有5个类别
        ]

    def update_state(self, y_true, y_pred, sample_weight=None):
        y_pred = tf.argmax(y_pred, axis=1)
        for i in range(5):
            self.recalls[i].update_state(
                tf.cast(y_true == i, tf.float32),
                tf.cast(y_pred == i, tf.float32),
                sample_weight
            )

    def result(self):
        return tf.reduce_mean([r.result() for r in self.recalls])

    def reset_state(self):
        for r in self.recalls:
            r.reset_state()

class MacroF1(metrics.Metric):
    def __init__(self, name='macro_f1', **kwargs):
        super().__init__(name=name, **kwargs)
        self.precision = MacroPrecision()
        self.recall = MacroRecall()

    def update_state(self, y_true, y_pred, sample_weight=None):
        self.precision.update_state(y_true, y_pred, sample_weight)
        self.recall.update_state(y_true, y_pred, sample_weight)

    def result(self):
        p = self.precision.result()
        r = self.recall.result()
        return 2 * (p * r) / (p + r + 1e-6)

    def reset_state(self):
        self.precision.reset_state()
        self.recall.reset_state()

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
            metrics=[
                'accuracy',
                MacroPrecision(),
                MacroRecall(),
                MacroF1(),
            ]
        )

        # 回调函数
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_accuracy', patience=1, restore_best_weights=True),
            tf.keras.callbacks.ModelCheckpoint(
                str(fold_dir / 'best_model.h5'), save_best_only=True),
            tf.keras.callbacks.CSVLogger(str(fold_dir / 'training_log.csv'))
        ]

        # 训练
        history = model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=1,
            batch_size=32,
            callbacks=callbacks,
            class_weight=class_weights_dict,
            verbose=1
        )
        # 在model.fit之后添加以下代码

        # 加载最佳模型
        model = tf.keras.models.load_model(
            str(fold_dir / 'best_model.h5'),
            custom_objects={
                'focal_loss': focal_loss,
                'MacroPrecision': MacroPrecision,
                'MacroRecall': MacroRecall,
                'MacroF1': MacroF1,
            }
        )

        # 评估验证集
        eval_results = model.evaluate(X_val, y_val, verbose=0)
        metrics_dict = dict(zip(model.metrics_names, eval_results))

        # 保存指标结果
        val_acc = metrics_dict['accuracy']
        val_precision = metrics_dict['macro_precision']
        val_recall = metrics_dict['macro_recall']
        val_f1 = metrics_dict['macro_f1']
        fold_results.append({
            'val_acc': val_acc,
            'val_precision': val_precision,
            'val_recall': val_recall,
            'val_f1': val_f1,
        })

        # 生成预测结果用于分类报告和混淆矩阵
        y_val_pred = model.predict(X_val)
        y_val_pred_labels = np.argmax(y_val_pred, axis=1)

        # 生成分类报告和混淆矩阵


        class_names = ['W', 'N1', 'N2', 'N3', 'R']
        report = classification_report(y_val, y_val_pred_labels, target_names=class_names, output_dict=True)
        report_df = pd.DataFrame(report).transpose()
        report_df.to_csv(fold_dir / 'classification_report.csv')

        cm = confusion_matrix(y_val, y_val_pred_labels)
        np.save(fold_dir / 'confusion_matrix.npy', cm)

        # 绘制混淆矩阵图（需要matplotlib）
        try:
            plt.figure(figsize=(10, 8))
            plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
            plt.title('Confusion Matrix')
            plt.colorbar()
            tick_marks = np.arange(len(class_names))
            plt.xticks(tick_marks, class_names, rotation=45)
            plt.yticks(tick_marks, class_names)
            plt.xlabel('Predicted Label')
            plt.ylabel('True Label')
            plt.tight_layout()
            plt.savefig(fold_dir / 'confusion_matrix.png')
            plt.close()
        except ImportError:
            print("Matplotlib未安装，跳过混淆矩阵绘图。")
        # 记录结果
        # val_acc = max(history.history['val_accuracy'])
        # fold_results.append(val_acc)
        print(f"Fold {fold_idx + 1} 最佳验证准确率: {val_acc:.4f}")

        # ========== 新增内存回收代码 ==========
        del model, X_train, y_train, X_val, y_val, scaler
        gc.collect()
        tf.keras.backend.clear_session()
        # ====================================
    # 输出最终结果
    print("\n=== 交叉验证结果 ===")

    # 提取各指标数值
    val_acc_list = [res['val_acc'] for res in fold_results]
    val_precision_list = [res['val_precision'] for res in fold_results]
    val_recall_list = [res['val_recall'] for res in fold_results]
    val_f1_list = [res['val_f1'] for res in fold_results]

    print(f"验证准确率: {val_acc_list}")
    print(f"平均验证准确率: {np.mean(val_acc_list):.4f} ± {np.std(val_acc_list):.4f}")

    print(f"\n验证宏精确率: {val_precision_list}")
    print(f"平均宏精确率: {np.mean(val_precision_list):.4f} ± {np.std(val_precision_list):.4f}")

    print(f"\n验证宏召回率: {val_recall_list}")
    print(f"平均宏召回率: {np.mean(val_recall_list):.4f} ± {np.std(val_recall_list):.4f}")

    print(f"\n验证宏F1分数: {val_f1_list}")
    print(f"平均宏F1分数: {np.mean(val_f1_list):.4f} ± {np.std(val_f1_list):.4f}")


if __name__ == "__main__":
    main()