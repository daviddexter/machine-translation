from keras.layers import Layer, Dropout, Concatenate
from keras import activations, initializers, regularizers, constraints
from keras.engine import InputSpec
import keras.backend as K

class BaseMultiHeadAttention(Layer):
    """Attention Layer"""

    def __init__(self, output_dim: int, num_heads: int, 
                dropout: float=0.1,
                activation=None,
                kernel_initializer='glorot_uniform',
                bias_initializer='zeros',
                kernel_regularizer=None,
                bias_regularizer=None,
                activity_regularizer=None,
                kernel_constraint=None,
                bias_constraint=None,
                **kwargs
                ):
        if output_dim % num_heads != 0:
            raise ValueError("Hidden size must be evenly divisible by num of heads")
        self.output_dim = output_dim
        self.num_heads = num_heads
        self.dropout = dropout
        self.activation = activations.get(activation)
        self.kernel_initializer = initializers.get(kernel_initializer)
        self.bias_initializer = initializers.get(bias_initializer)
        self.kernel_regularizer = regularizers.get(kernel_regularizer)
        self.bias_regularizer = regularizers.get(bias_regularizer)
        self.activity_regularizer = regularizers.get(activity_regularizer)
        self.kernel_constraint = constraints.get(kernel_constraint)
        self.bias_constraint = constraints.get(bias_constraint)
        super(BaseMultiHeadAttention, self).__init__(**kwargs)

    def build(self, input_shape):
        if not (isinstance(input_shape, list) and ( len(input_shape)  == 2 or len(input_shape) == 3 )):
            raise ValueError(
                'You must call this layer passing a list of two or three tensors'
                '(for keys/values and queries)')
        """if input_shape[0][-1] != input_shape[1][-1]:
            raise ValueError(
                'The inputs and outputs must be the same dimensionality' 
            )"""
        self.batch_size, self.timesteps, self.input_dim = input_shape[0]
        self.W_q = self.add_weight(shape=(self.input_dim, self.output_dim),
                                    name='W_q',
                                    initializer=self.kernel_initializer,
                                    regularizer=self.kernel_regularizer,
                                    constraint=self.kernel_constraint)

        self.W_k = self.add_weight(shape=(self.input_dim, self.output_dim),
                                    name='W_k',
                                    initializer=self.kernel_initializer,
                                    regularizer=self.kernel_regularizer,
                                    constraint=self.kernel_constraint)

        self.W_v = self.add_weight(shape=(self.input_dim, self.output_dim),
                                    name='W_v',
                                    initializer=self.kernel_initializer,
                                    regularizer=self.kernel_regularizer,
                                    constraint=self.kernel_constraint)

        self.W_o = self.add_weight(shape=(self.output_dim, self.output_dim),
                                    name='W_o',
                                    initializer=self.kernel_initializer,
                                    regularizer=self.kernel_regularizer,
                                    constraint=self.kernel_constraint)
        if len(input_shape) == 2:
            self.input_spec = [InputSpec(min_ndim=3, axes={-1: self.input_dim}), InputSpec(min_ndim=3, axes={-1: self.input_dim})]
        else:
            self.input_spec = [InputSpec(min_ndim=3, axes={-1: self.input_dim}), InputSpec(min_ndim=3, axes={-1: self.input_dim}), InputSpec(min_ndim=4, axes={-1: input_shape[2][-1]})]
        self.built = True


    def split_heads(self, x):
        """ Split x into different 
        Args:
            x: input with shape [batch_size, timesteps, output_dim]
        Returns:
            output: tensor with shape [batch_size, num_heads, timesteps, output_dim/num_heads]
        """
        batch_size = K.shape(x)[0]
        length = K.shape(x)[1]
        depth = self.output_dim // self.num_heads

        x = K.reshape(x, (batch_size, length, self.num_heads, depth))
        output = K.permute_dimensions(x, (0, 2, 1, 3))
        return output

    def combine_heads(self, x):
        """Combine x that has been split
         Args:
            x: input with shape [batch_size, num_heads, timesteps, output_dim/num_heads]
        Returns:
            output: tensor with shape [batch_size, timesteps, output_dim]
        """
        batch_size = K.shape(x)[0]
        length = K.shape(x)[2]
        x = K.permute_dimensions(x, (0, 2, 1, 3))
        output = K.reshape(x, (batch_size, length, self.output_dim))
        return output

    def call(self, input_tensor, training=None):
        if not (isinstance(input_tensor, list) and ( len(input_tensor)  == 2 or len(input_tensor) == 3 )):
            raise ValueError(
                'You must call this layer passing a list of two or three tensors'
                '(for keys/values and queries)')
        if len(input_tensor) == 2:
            x, y = input_tensor
            bias = None
        else:
            x, y, bias = input_tensor
        q = K.dot(x, self.W_q)
        k = K.dot(y, self.W_k)
        v = K.dot(y, self.W_v)

        q = self.split_heads(q)
        k = self.split_heads(k)
        v = self.split_heads(v)

        depth = self.output_dim // self.num_heads
        q *= depth ** -0.5
        k = K.permute_dimensions(k, (0, 1, 3, 2))
        logits = K.batch_dot(q, k)
        if bias is not None:
            logits += bias
        weights = K.softmax(logits)

        if 0. < self.dropout < 1.:
            def dropped_inputs():
                return K.dropout(weights, self.dropout)
            weights = K.in_train_phase(weights, dropped_inputs, training)
        
        attention_output = K.batch_dot(weights, v)
        #Recombine head
        attention_output = self.combine_heads(attention_output)
        output = K.dot(attention_output, self.W_o)
        return output

    def compute_output_shape(self, input_shape):
        return (None, self.timesteps, self.output_dim)

    def get_config(self):
        config = {
            'num_heads': self.num_heads,
            'output_dim': self.output_dim,
            'dropout': self.dropout
        }
        base_config = super(BaseMultiHeadAttention, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))

class MultiHeadAttention(BaseMultiHeadAttention):
    def __init__(self, output_dim: int, num_heads: int, 
                **kwargs):
        super(MultiHeadAttention, self).__init__(output_dim, num_heads, **kwargs)

    def build(self, input_shape):
        super(MultiHeadAttention, self).build(input_shape)

    def call(self, x):
        return super(MultiHeadAttention, self).call(x)

    def compute_output_shape(self, input_shape):
        return super(MultiHeadAttention, self).compute_output_shape(input_shape)

    def get_config(self):
        return super(MultiHeadAttention, self).get_config()

class MultiHeadSelfAttention(BaseMultiHeadAttention):
    def __init__(self, output_dim: int, num_heads: int, 
                **kwargs):
        super(MultiHeadSelfAttention, self).__init__(output_dim, num_heads, **kwargs)

    def build(self, input_shape):
        if isinstance(input_shape, list):
            _, self.length, self.input_dim = input_shape[0]
            super(MultiHeadSelfAttention, self).build([input_shape[0], input_shape[0], input_shape[1]])
            self.input_spec = [InputSpec(min_ndim=3, axes={-1: self.input_dim}), InputSpec(min_ndim=3, axes={-1: self.length})]
        else:
            self.input_dim = input_shape[-1]
            super(MultiHeadSelfAttention, self).build([input_shape, input_shape])
            self.input_spec = [InputSpec(min_ndim=3, axes={-1: self.input_dim})]

    def call(self, x):
        if isinstance(x, list):
            return super(MultiHeadSelfAttention, self).call([x[0], x[0], x[1]])
        else:
            return super(MultiHeadSelfAttention, self).call([x, x])

    def compute_output_shape(self, input_shape):
        return super(MultiHeadSelfAttention, self).compute_output_shape([input_shape, input_shape])

    def get_config(self):
        return super(MultiHeadSelfAttention, self).get_config()

if __name__ == "__main__":
    from keras.layers import Input, LSTM, Embedding
    from keras.models import Model
    from keras.layers.wrappers import Bidirectional
    from masking import Masking
    inp = Input(shape=(100,), dtype='float32')
    out = Input(shape=(125,), dtype='float32')
    masking = Masking()(inp)
    emb = Embedding(1000, 64)
    i = emb(inp)
    d = emb(out)
    encode = Bidirectional(LSTM(64, return_sequences=True), merge_mode='concat')(i)
    decode = Bidirectional(LSTM(64, return_sequences=True), merge_mode='concat')(d)
    dec = MultiHeadAttention(32, 4, dropout=0.1)([decode, encode, masking])
    model = Model(inputs=[inp, out], outputs=dec)
    print(model.summary())