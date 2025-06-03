import tensorflow as tf
from tensorflow.keras import backend as K
import numpy as np
def weighted_categorical_crossentropy(weights):
    weights = K.variable(weights)

    def loss(y_true, y_pred):
        y_pred /= K.sum(y_pred, axis=-1, keepdims=True)
        y_pred = K.clip(y_pred, K.epsilon(), 1 - K.epsilon())
        loss = y_true * K.log(y_pred) * weights
        loss = -K.sum(loss, -1)
        return loss

    return loss


def resnet_se_block(inputs, num_filters, kernel_size, strides, ratio):
    x = tf.keras.layers.Conv1D(
        filters=num_filters, kernel_size=kernel_size, strides=strides,
        padding='same', kernel_initializer='he_normal'
    )(inputs)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation('relu')(x)
    x = tf.keras.layers.Conv1D(
        filters=num_filters, kernel_size=kernel_size, strides=strides,
        padding='same', kernel_initializer='he_normal'
    )(x)
    x = tf.keras.layers.BatchNormalization()(x)

    se = tf.keras.layers.Lambda(lambda x: K.mean(x, axis=-2, keepdims=True))(x)
    se = tf.keras.layers.Dense(units=num_filters // ratio)(se)
    se = tf.keras.layers.Activation('relu')(se)
    se = tf.keras.layers.Dense(units=num_filters)(se)
    se = tf.keras.layers.Activation('sigmoid')(se)
    x = tf.keras.layers.multiply([x, se])

    x_skip = tf.keras.layers.Conv1D(
        filters=num_filters, kernel_size=1, strides=1,
        padding='same', kernel_initializer='he_normal'
    )(inputs)
    x_skip = tf.keras.layers.BatchNormalization()(x_skip)

    x = tf.keras.layers.Add()([x, x_skip])
    x = tf.keras.layers.Activation('relu')(x)
    return x


def create_model(Fs=100, n_classes=5, seq_length=15, summary=True):
    x_input = tf.keras.Input(shape=(seq_length, 30 * Fs, 1))

    x = resnet_se_block(x_input, 32, 3, 1, 4)
    x = tf.keras.layers.MaxPool2D(
        pool_size=(4, 1), strides=(4, 1), padding='same', data_format='channels_first' #cpu训练时改为 channels_last
    )(x)

    x = resnet_se_block(x, 64, 5, 1, 4)
    x = tf.keras.layers.MaxPool2D(
        pool_size=(4, 1), strides=(4, 1), padding='same', data_format='channels_first' #cpu训练时改为 channels_last
    )(x)

    x = resnet_se_block(x, 128, 7, 1, 4)
    x = tf.keras.layers.Lambda(lambda x: K.mean(x, axis=-2, keepdims=False))(x)
    x = tf.keras.layers.Dropout(rate=0.5)(x)

    x = tf.keras.layers.LSTM(units=64, dropout=0.5, activation='relu', return_sequences=True)(x)
    x_out = tf.keras.layers.Dense(units=n_classes, activation='softmax')(x)

    model = tf.keras.models.Model(x_input, x_out)
    model.compile(
        optimizer='adam',
        loss=weighted_categorical_crossentropy(np.array([1, 1.5, 1, 1, 1])),
        metrics=['accuracy']
    )

    if summary:
        model.summary()
        tf.keras.utils.plot_model(model, show_shapes=True, dpi=300, to_file='model.png')

    return model