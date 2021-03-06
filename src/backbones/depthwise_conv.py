import tensorflow as tf


@tf.contrib.framework.add_arg_scope
def depthwise_conv(
        x, kernel=3, stride=1, padding='SAME',
        activation_fn=None, normalizer_fn=None,
        data_format='NCHW', scope='depthwise_conv'):

    with tf.variable_scope(scope):
        assert data_format == 'NCHW'
        in_channels = x.shape.as_list()[1]
        W = tf.get_variable(
            'depthwise_weights',
            [kernel, kernel, in_channels, 1],
            dtype=tf.float32,
            initializer=tf.contrib.layers.xavier_initializer()
        )
        x = tf.nn.depthwise_conv2d(x, W, [1, 1, stride, stride], padding, data_format='NCHW')
        x = normalizer_fn(x) if normalizer_fn is not None else x  # batch normalization
        x = activation_fn(x) if activation_fn is not None else x  # nonlinearity
        return x
