"""
Convolutional Neural Network for facial landmarks detection.
"""
import argparse

import cv2
import numpy as np
import tensorflow as tf
from tensorflow import keras

from model import LandmarkModel

# Add arguments parser to accept user specified arguments.
parser = argparse.ArgumentParser()
parser.add_argument('--train_record', default='train.record', type=str,
                    help='Training record file')
parser.add_argument('--val_record', default='validation.record', type=str,
                    help='validation record file')
parser.add_argument('--model_dir', default='./train', type=str,
                    help='training model directory')
parser.add_argument('--log', default='./log', type=str,
                    help='training log directory')
parser.add_argument('--export_dir', default=None, type=str,
                    help='directory to export the saved model')
parser.add_argument('--train_steps', default=1000, type=int,
                    help='training steps')
parser.add_argument('--epochs', default=None, type=int,
                    help='epochs for training')
parser.add_argument('--batch_size', default=16, type=int,
                    help='training batch size')
parser.add_argument('--raw_input', default=False, type=bool,
                    help='Use raw tensor as model input.')
args = parser.parse_args()


# CAUTION: The image width, height and channels should be consist with your
# training data. Here they are set as 128 to be complied with the tutorial.
# Mismatching of the image size will cause error of mismatching tensor shapes.
IMG_WIDTH = 128
IMG_HEIGHT = 128
IMG_CHANNEL = 3

# The number of facial landmarks the model should output. By default the mark is
# in 2D space.
MARK_SIZE = 68


def get_compiled_model(output_size):
    """Return a compiled landmark model.
    Args:
        output_size: the total number of landmarks coordinates (x + y).

    Returns:
        a compiled keras model.
    """
    # Construct the network.
    model = LandmarkModel(output_size)
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=0.001),
                  loss=keras.losses.mean_squared_error,
                  metrics=[keras.metrics.mean_squared_error])

    return model


def _parse(example):
    """Extract data from a `tf.Example` protocol buffer.
    Args:
        example: a protobuf example.

    Returns:
        a parsed data and label pair.
    """
    # Defaults are not specified since both keys are required.
    keys_to_features = {
        'image/filename': tf.io.FixedLenFeature([], tf.string),
        'image/encoded': tf.io.FixedLenFeature([], tf.string),
        'label/marks': tf.io.FixedLenFeature([136], tf.float32),
    }
    parsed_features = tf.io.parse_single_example(example, keys_to_features)

    # Extract features from single example
    image_decoded = tf.image.decode_image(parsed_features['image/encoded'])
    image_reshaped = tf.reshape(
        image_decoded, [IMG_HEIGHT, IMG_WIDTH, IMG_CHANNEL])
    points = tf.cast(parsed_features['label/marks'], tf.float32)

    return image_reshaped, points


def get_parsed_dataset(record_file, batch_size, epochs=None, shuffle=True):
    """Return a parsed dataset for model.
    Args:
        record_file: the TFRecord file.
        batch_size: batch size.
        epochs: epochs of dataset.
        shuffle: whether to shuffle the data.

    Returns:
        a parsed dataset.
    """
    # Init the dataset from the TFRecord file.
    dataset = tf.data.TFRecordDataset(record_file)

    # Use `Dataset.map()` to build a pair of a feature dictionary and a label
    # tensor for each example.
    if shuffle is True:
        dataset = dataset.shuffle(buffer_size=10000)
    dataset = dataset.map(
        _parse, num_parallel_calls=tf.data.experimental.AUTOTUNE)
    dataset = dataset.batch(batch_size)
    dataset = dataset.repeat(epochs)
    dataset = dataset.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)

    return dataset


def run():
    """Train, eval and export the model."""

    # Create the Model
    mark_model = get_compiled_model(MARK_SIZE*2)

    # Get the training data ready.
    dataset = get_parsed_dataset(record_file=args.train_record,
                                 batch_size=args.batch_size,
                                 epochs=args.epochs,
                                 shuffle=True)

    # To save and log the training process, we need some callbacks.
    callbacks = [keras.callbacks.TensorBoard(log_dir=args.log, update_freq=1024),
                 keras.callbacks.ModelCheckpoint(filepath=args.model_dir,
                                                 monitor='loss',
                                                 save_freq=4096)]

    # Train.
    print('Starting to train.')
    train_history = mark_model.fit(dataset,
                                   epochs=args.epochs,
                                   steps_per_epoch=args.train_steps,
                                   callbacks=callbacks)

    # Do evaluation after training.
    print('Starting to evaluate.')
    evaluation = mark_model.evaluate(dataset)
    print(evaluation)

    mark_model.summary()


if __name__ == '__main__':
    run()
