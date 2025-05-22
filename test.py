import tensorflow as tf
import numpy as np

print(f"TensorFlow版本: {tf.__version__}")
print(f"GPU可用: {tf.config.list_physical_devices('GPU')}")

# 验证基本功能
model = tf.keras.Sequential([
    tf.keras.layers.Dense(10, input_shape=(5,))
])
model.predict(np.random.rand(2,5))
print("测试通过！")