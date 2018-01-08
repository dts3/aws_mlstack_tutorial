#
#
# Templates for this file can be found here:
# http://docs.aws.amazon.com/sagemaker/latest/dg/mxnet-training-inference-code-template.html
#
# More information can be found here:
# https://github.com/aws/sagemaker-python-sdk#sagemaker-python-sdk-overview
#

import mxnet as mx
import numpy as np
import boto3

mnist = mx.test_utils.get_mnist()

# ---------------------------------------------------------------------------- #
# Training functions                                                           #
# ---------------------------------------------------------------------------- #

def train(
#    hyperparameters,
#    input_data_config,
    channel_input_dirs,
#    output_data_dir,
#    model_dir,
#    num_gpus,
#    num_cpus,
#    hosts,
#    current_host,
    **kwargs):

    """
    [Required]

    Runs Apache MXNet training. Amazon SageMaker calls this function with information
    about the training environment. When called, if this function returns an
    object, that object is passed to a save function.  The save function
    can be used to serialize the model to the Amazon SageMaker training job model
    directory.

    The **kwargs parameter can be used to absorb any Amazon SageMaker parameters that
    your training job doesn't need to use. For example, if your training job
    doesn't need to know anything about the training environment, your function
    signature can be as simple as train(**kwargs).

    Amazon SageMaker invokes your train function with the following python kwargs:

    Args:
        - hyperparameters: The Amazon SageMaker Hyperparameters dictionary. A dict
            of string to string.
        - input_data_config: The Amazon SageMaker input channel configuration for
            this job.
        - channel_input_dirs: A dict of string-to-string maps from the
            Amazon SageMaker algorithm input channel name to the directory containing
            files for that input channel. Note, if the Amazon SageMaker training job
            is run in PIPE mode, this dictionary will be empty.
        - output_data_dir:
            The Amazon SageMaker output data directory. After the function returns, data written to this
            directory is made available in the Amazon SageMaker training job
            output location.
        - model_dir: The Amazon SageMaker model directory. After the function returns, data written to this
            directory is made available to the Amazon SageMaker training job
            model location.
        - num_gpus: The number of GPU devices available on the host this script
            is being executed on.
        - num_cpus: The number of CPU devices available on the host this script
            is being executed on.
        - hosts: A list of hostnames in the Amazon SageMaker training job cluster.
        - current_host: This host's name. It will exist in the hosts list.
        - kwargs: Other keyword args.

    Returns:
        - (object): Optional. An Apache MXNet model to be passed to the model
            save function. If you do not return anything (or return None),
            the save function is not called.
    """

    #bucket_name = 'jakechenawspublic'
    #key_name = 'sample_data/mnist/mnist_train.csv'

    s3 = boto3.client('s3')
    s3.download_file(bucket_name, key_name, 'mnist_train.csv')
    # load downloaded files into s3
    fnames = glob('*.csv')
    arrays = np.array([np.loadtxt(f, delimiter=',') for f in fnames])

    """
    Copy/paste from tutorial part 1
    """
    # join files into one array with shape [records, 785]
    # 785 because each record has 28x28=784 pixels and 1 label
    mnist_train = arrays.reshape(-1, 785)

    # split record into image data and label
    X_train = mnist_train.T[1:].T.reshape(-1,1,28,28)
    y_train = mnist_train.T[:1].T.reshape(-1)

    # wrap mxnet iterator around records
    batch_size = 100
    train_iter = mx.io.NDArrayIter(X_train[:-1000], y_train[:-1000], batch_size, shuffle=True)
    val_iter = mx.io.NDArrayIter(X_train[-1000:], y_train[-1000:], batch_size)

    # define network
    data = mx.sym.var('data')
    # first conv layer
    conv1 = mx.sym.Convolution(data=data, kernel=(5,5), num_filter=20)
    tanh1 = mx.sym.Activation(data=conv1, act_type="tanh")
    pool1 = mx.sym.Pooling(data=tanh1, pool_type="max", kernel=(2,2), stride=(2,2))
    # second conv layer
    conv2 = mx.sym.Convolution(data=pool1, kernel=(5,5), num_filter=50)
    tanh2 = mx.sym.Activation(data=conv2, act_type="tanh")
    pool2 = mx.sym.Pooling(data=tanh2, pool_type="max", kernel=(2,2), stride=(2,2))
    # first fullc layer
    flatten = mx.sym.flatten(data=pool2)
    fc1 = mx.symbol.FullyConnected(data=flatten, num_hidden=500)
    tanh3 = mx.sym.Activation(data=fc1, act_type="tanh")
    # second fullc
    fc2 = mx.sym.FullyConnected(data=tanh3, num_hidden=10)
    # softmax loss
    lenet = mx.sym.SoftmaxOutput(data=fc2, name='softmax')
    # define training batch size
    batch_size = 100

    # create iterator around training and validation data
    train_iter = mx.io.NDArrayIter(mnist['train_data'][:ntrain], mnist['train_label'][:ntrain], batch_size, shuffle=True)
    val_iter = mx.io.NDArrayIter(mnist['train_data'][ntrain:], mnist['train_label'][ntrain:], batch_size)

    """
    End copy/paste from part 1
    """
    # create a trainable module
    # toggle this between mx.cpu() and mx.gpu() depending on if you're using ml.c-family or ml.p-family for training.
    context=mx.gpu()
    # toggle this between 'local', 'device', 'dist-sync', or 'dist-device-sync' 
    # depending on if you're using ml.c-family or ml.p-family for training.
    # https://mxnet.incubator.apache.org/how_to/multi_devices.html
    kvstore='device'
    
    lenet_model = mx.mod.Module(symbol=lenet, context=context)
    lenet_model.fit(train_iter,
                    eval_data=val_iter,
                    optimizer='sgd',
                    optimizer_params={'learning_rate':0.1},
                    eval_metric='acc',
                    batch_end_callback = mx.callback.Speedometer(batch_size, 100),
                    num_epoch=10,
                    kvstore=kvstore
                   )
    
    return lenet


# ---------------------------------------------------------------------------- #
# Hosting functions                                                            #
# ---------------------------------------------------------------------------- #


def model_fn(model_dir):

    """
    [Optional]

    Loads a model from disk, reading from model_dir. Called once by each
    inference service worker when it is started.

    If you want to take advantage of Amazon SageMaker's default request handling
    functions, the returned object should be a `Gluon Block
    <https://mxnet.incubator.apache.org/api/python/gluon/gluon.html#mxnet.gluon.Block>
    or MXNet `Module <https://mxnet.incubator.apache.org/api/python/module.html>`,
     described below. If you are providing your own transform_fn,
    then your model_fn can return anything that is compatible with your
     transform_fn.

    Amazon SageMaker provides a default model_fn that works with the serialization
    format used by the Amazon SageMaker default save function, discussed above. If
    you saved your model using the default save function, you do not need to
    provide a model_fn in your hosting script.

    Args:
        - model_dir: The Amazon SageMaker model directory.

    Returns:
        - (object): Optional. The deserialized model.
    """
    pass


def transform_fn(model, input_data, content_type, accept):
    """
    [Optional]

    Transforms input data into a prediction result. Amazon SageMaker invokes your
    transform_fn in response to an InvokeEndpoint operation on an Amazon SageMaker
    endpoint containing this script. Amazon SageMaker passes in the model, previously
    loaded with model_fn, along with the input data, request content type, and accept content type from the InvokeEndpoint request.

    The input data is expected to have the given content_type.

    The output returned should have the given accept content type.

    This function should return a tuple of (transformation result, content
    type). In most cases, the returned content type should be the same as the
    accept content type, but it might differ. For example, when your code needs to
    return an error response.

    If you provide a transform_fn in your hosting script, it will be used
    to handle the entire request. You don't need to provide any other
    request handling functions (input_fn, predict_fn, or output_fn).
    If you do provide them, they will be ignored.

    Amazon SageMaker provides default transform_fn implementations that work with
    Gluon and Module models. These support JSON input and output, and for Module
    models, also CSV. To use the default transform_fn, provide a
    hosting script without a transform_fn or any other request handling
    functions. For more information about the default transform_fn,
    see the SageMaker Python SDK GitHub documentation. 

    Args:
        - input_data: The input data from the payload of the
            InvokeEndpoint request.
        - content_type: The content type of the request.
        - accept: The content type from the request's Accept header.

    Returns:
        - (object, string): A tuple containing the transformed result
            and its content type
    """
    pass


# ---------------------------------------------------------------------------- #
# Request handlers for Module models                                           #
# ---------------------------------------------------------------------------- #

def input_fn(model, input_data, content_type):
    """
    [Optional]

    Prepares data for transformation. Amazon SageMaker invokes your input_fn in
    response to an InvokeEndpoint operation on an Amazon SageMaker endpoint that contains
    this script. Amazon SageMaker passes in the MXNet Module returned by your
    model_fn, along with the input data and content type from the
    InvokeEndpoint request.

    The function should return an NDArray. Amazon SageMaker wraps the returned
    NDArray in a DataIter with a batch size that matches your model, and then
    passes it to your predict_fn.

    If you omit this function, Amazon SageMaker provides a default implementation.
    The default input_fn converts a JSON or CSV-encoded array data into an
    NDArray. For more information about the default input_fn, see the
    Amazon SageMaker Python SDK GitHub documentation. 

    Args:
        - model: A Module; the result of calling model_fn on this script.
        - input_data: The input data from the payload of the
            InvokeEndpoint request.
        - content_type: The content type of the request.

    Returns:
        - (NDArray): an NDArray
    """
    pass


def predict_fn(module, data):
    """
    [Optional]

    Performs prediction on an MXNet DataIter object. In response to an
    InvokeEndpoint request, Amazon SageMaker invokes your
    predict_fn with the model returned by your model_fn and DataIter
    that contains the result of the input_fn.

    The function should return a list of NDArray or a list of list of NDArray
    containing the prediction results. For more information, see the MXNet Module API
    <https://mxnet.incubator.apache.org/api/python/module.html#mxnet.module.BaseModule.predict>.

    If you omit this function, Amazon SageMaker provides a default implementation.
    The default predict_fn calls module.predict on the input
    data and returns the result.

    Args:
        - module (Module): The loaded MXNet Module; the result of calling
            model_fn on this script.
        - data (DataIter): A DataIter containing the results of a
            call to input_fn.

    Returns:
        - (object): A list of NDArray or list of list of NDArray
            containing the prediction results.
    """
    pass


def output_fn(data, accept):
    """
    [Optional]

    Serializes prediction results. Amazon SageMaker invokes your output_fn with the
    results of predict_fn and the content type from the InvokeEndpoint
    request's accept header.

    This function should return a tuple of (transformation result, content
    type). In most cases, the returned content type should be the same as the
    accept content type, but it might differ. For example, when your code needs to
    return an error response.

    If you omit this function, Amazon SageMaker provides a default implementation.
    The default output_fn converts the prediction result into JSON or CSV-
    encoded array data, depending on the value of the accept header. For more
    information about the default input_fn, see the Amazon SageMaker Python SDK
    GitHub documentation. 

    Args:
        - data: A list of NDArray or list of list of NDArray. The result of
            calling predict_fn.
        - content_type: A string. The content type from the InvokeEndpoint
            request's Accept header.

    Returns:
        - (object, string): A tuple containing the transformed result
            and its content type.
    """
    pass