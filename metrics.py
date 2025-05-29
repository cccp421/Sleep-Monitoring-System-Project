from tensorflow.keras import metrics
import tensorflow as tf

class MacroPrecision(metrics.Metric):
    def __init__(self, name='macro_precision', num_classes=5, **kwargs):
        super().__init__(name=name, **kwargs)
        self.num_classes = num_classes
        self.precisions = [
            metrics.Precision(class_id=i)
            for i in range(num_classes)
        ]

    def update_state(self, y_true, y_pred, sample_weight=None):
        y_pred = tf.argmax(y_pred, axis=1)
        for i in range(self.num_classes):
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
    def __init__(self, name='macro_recall', num_classes=5, **kwargs):
        super().__init__(name=name, **kwargs)
        self.num_classes = num_classes
        self.recalls = [
            metrics.Recall(class_id=i)
            for i in range(num_classes)
        ]

    def update_state(self, y_true, y_pred, sample_weight=None):
        y_pred = tf.argmax(y_pred, axis=1)
        for i in range(self.num_classes):
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
    def __init__(self, name='macro_f1', num_classes=5, **kwargs):
        super().__init__(name=name, **kwargs)
        self.precision = MacroPrecision(num_classes=num_classes)
        self.recall = MacroRecall(num_classes=num_classes)

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