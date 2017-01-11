import tensorflow as tf
import numpy as np


def weight_variable(name, shape):
    return tf.get_variable(name, shape, initializer=tf.contrib.layers.xavier_initializer())

def linear(name, x, shape):
    w = weight_variable(name+"W", shape)
    b = weight_variable(name+"B", [shape[1]])
    return tf.matmul(x,w) + b

def embedding_variable(name, shape):
    return tf.get_variable(name, shape = shape, initializer = tf.random_normal_initializer(stddev=0.1))

class NCRModel():
    def get_HPO_embedding(self, indices=None):
        embedding = self.HPO_embedding
        if indices is not None:
            embedding = tf.gather(self.HPO_embedding, indices)
            return embedding #tf.maximum(0.0, embedding)

    def apply_meanpool(self, seq, seq_length):
        filters1 = tf.get_variable('conv1', [1, self.config.word_embed_size, self.config.hidden_size], tf.float32, initializer=tf.contrib.layers.xavier_initializer())
        layer1 = tf.nn.tanh(tf.nn.conv1d(seq, filters1, 1, padding='SAME'))

        filters2 = tf.get_variable('conv2', [1, self.config.hidden_size, self.config.hidden_size], tf.float32, initializer=tf.contrib.layers.xavier_initializer())
        layer2 = tf.nn.tanh(tf.nn.conv1d(layer1, filters2, 1, padding='SAME'))

        return tf.reduce_max(layer2, [1])

    #############################
    ##### Creates the model #####
    #############################
    def __init__(self, config, training = False):
        self.config = config
        self.ancestry_masks = tf.get_variable("ancestry_masks", [config.hpo_size, config.hpo_size], trainable=False)

        ### Inputs ###
        self.input_hpo_id = tf.placeholder(tf.int32, shape=[None])
        self.input_sequence = tf.placeholder(tf.float32, shape=[None, config.max_sequence_length, config.word_embed_size])
        self.input_sequence_lengths = tf.placeholder(tf.int32, shape=[None])
        label = tf.one_hot(self.input_hpo_id, config.hpo_size)

        #gru_state = self.apply_rnn(self.input_sequence, self.input_sequence_lengths) 
        gru_state = self.apply_meanpool(self.input_sequence, self.input_sequence_lengths) 

        layer1 = tf.nn.tanh(linear('sm_layer1', gru_state, [self.config.hidden_size, self.config.layer1_size]))
        layer2 = tf.nn.tanh(linear('sm_layer2', layer1, [self.config.layer1_size, self.config.layer2_size]))
#        layer3 = tf.nn.relu(linear('sm_layer3', layer2, [self.config.layer2_size, self.config.layer3_size]))
        self.layer4= (linear('sm_layer4', layer2, [self.config.layer2_size, self.config.hpo_size]))
        #self.layer4= tf.nn.tanh(linear('sm_layer4', layer3, [self.config.layer3_size, self.config.hpo_size]))

        mixing_w = tf.Variable(1.0)

        self.score_layer = (mixing_w * self.layer4 +\
                tf.matmul(self.layer4, tf.transpose(self.ancestry_masks)))
        '''
        self.score_layer = tf.matmul(self.layer4, tf.transpose(self.ancestry_masks))
        '''

        self.pred = tf.nn.softmax(self.score_layer)

        if training:
            self.loss = tf.reduce_mean(\
                    tf.nn.softmax_cross_entropy_with_logits(self.score_layer, label))


