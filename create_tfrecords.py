import io
import os
import PIL.Image
import tensorflow as tf
import json
import argparse
from tqdm import tqdm
import sys


"""
The purpose of this script is to create a .tfrecords file from a folder of images and
a folder of annotations. Annotations are in the json format.

Example of a json annotation (with filename "132416.json"):
{
  "object": [
    {"bndbox": {"ymin": 20, "ymax": 276, "xmax": 1219, "xmin": 1131}, "name": "dog"},
    {"bndbox": {"ymin": 1, "ymax": 248, "xmax": 1149, "xmin": 1014}, "name": "person"}
  ],
  "filename": "132416.jpg",
  "size": {"depth": 3, "width": 1920, "height": 1080}
}

Example of use:
python create_tfrecords.py \
    --image_dir=/home/dan/datasets/BBA/images_val/ \
    --annotations_dir=/home/dan/datasets/BBA/annotations_val/ \
    --output=data/val.tfrecords \
    --labels=data/labels.txt

labels is a .txt file where each line is a class name.
"""


def make_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i', '--image_dir', type=str, default='data/images'
    )
    parser.add_argument(
        '-a', '--annotations_dir', type=str, default='data/annotations'
    )
    parser.add_argument(
        '-o', '--output', type=str, default='data/data.tfrecords'
    )
    parser.add_argument(
        '-l', '--labels', type=str, default='data/labels.txt'
    )
    return parser.parse_args()


def dict_to_tf_example(annotation, image_dir, labels):
    """Convert dict to tf.Example proto.

    Notice that this function normalizes the bounding
    box coordinates provided by the raw data.

    Arguments:
        data: a dict.
        image_dir: a string, path to the image directory.
        labels: a dict, class name -> unique integer.
    Returns:
        an instance of tf.Example.
    """
    image_name = annotation['filename']
    assert image_name.endswith('.jpg') or image_name.endswith('.jpeg')

    image_path = os.path.join(image_dir, image_name)
    with tf.gfile.GFile(image_path, 'rb') as f:
        encoded_jpg = f.read()

    # check image format
    encoded_jpg_io = io.BytesIO(encoded_jpg)
    image = PIL.Image.open(encoded_jpg_io)
    if image.format != 'JPEG':
        raise ValueError('Image format not JPEG!')

    width = int(annotation['size']['width'])
    height = int(annotation['size']['height'])
    assert width > 0 and height > 0
    assert image.size[0] == width and image.size[1] == height
    ymin, xmin, ymax, xmax, classes = [], [], [], [], []

    just_name = image_name[:-4] if image_name.endswith('.jpg') else image_name[:-5]
    annotation_name = just_name + '.json'
    if len(annotation['object']) == 0:
        print(annotation_name, 'is without any objects!')

    for obj in annotation['object']:
        a = float(obj['bndbox']['ymin'])/height
        b = float(obj['bndbox']['xmin'])/width
        c = float(obj['bndbox']['ymax'])/height
        d = float(obj['bndbox']['xmax'])/width
        assert (a < c) and (b < d)

        ymin.append(a)
        xmin.append(b)
        ymax.append(c)
        xmax.append(d)
        try:
            classes.append(labels[obj['name']])
        except KeyError:
            print(annotation_name, 'has unknown label!')
            sys.exit(1)

    example = tf.train.Example(features=tf.train.Features(feature={
        'filename': _bytes_feature(image_name.encode()),
        'image': _bytes_feature(encoded_jpg),
        'xmin': _float_list_feature(xmin),
        'xmax': _float_list_feature(xmax),
        'ymin': _float_list_feature(ymin),
        'ymax': _float_list_feature(ymax),
        'labels': _int64_list_feature(classes),
    }))
    return example


def _bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def _int64_list_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=value))


def _float_list_feature(value):
    return tf.train.Feature(float_list=tf.train.FloatList(value=value))


def main():
    ARGS = make_args()

    with open(ARGS.labels, 'r') as f:
        labels = {line.strip(): i for i, line in enumerate(f.readlines()) if line.strip()}
    assert len(labels) > 0
    print('Possible labels (and label encoding):', labels)

    image_dir = ARGS.image_dir
    annotations_dir = ARGS.annotations_dir
    print('Reading images from:', image_dir)
    print('Reading annotations from:', annotations_dir, '\n')

    writer = tf.python_io.TFRecordWriter(ARGS.output)
    examples_list = os.listdir(annotations_dir)
    num_examples = 0
    for example in tqdm(examples_list):
        path = os.path.join(annotations_dir, example)
        annotation = json.load(open(path))
        tf_example = dict_to_tf_example(annotation, image_dir, labels)
        writer.write(tf_example.SerializeToString())
        num_examples += 1

    writer.close()
    print('Result is here:', ARGS.output)


main()
