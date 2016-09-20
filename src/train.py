# -*- coding: utf-8 -*-

from __future__ import division

"""
Script to train an RTE LSTM.

Input JSON files should be generated by the script `tokenize-corpus.py`.
"""

import argparse
import tensorflow as tf

import readdata
import utils
import multimlp

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('embeddings', help='Text file with word embeddings')
    parser.add_argument('train', help='JSONL or TSV file with training corpus')
    parser.add_argument('validation', help='JSONL or TSV file with validation corpus')
    parser.add_argument('save', help='Directory to save the model files')
    parser.add_argument('logs', help='Log directory to save summaries')

    # choose the model to be used
    parser.add_argument('-e', dest='num_epochs', default=10, type=int,
                        help='Number of epochs')
    parser.add_argument('-b', dest='batch_size', default=32, help='Batch size',
                        type=int)
    parser.add_argument('-u', dest='num_units', help='Number of hidden units',
                        default=100, type=int)
    parser.add_argument('-d', dest='dropout', help='Dropout probability', default=1.0,
                        type=float)
    parser.add_argument('-c', dest='clip_norm', help='Norm to clip training gradients',
                        default=None, type=float)
    parser.add_argument('-r', help='Learning rate', type=float, default=0.001, dest='rate')
    parser.add_argument('--use-intra', help='Use intra-sentence attention',
                        action='store_true', dest='use_intra')
    parser.add_argument('--l2', help='L2 normalization constant', type=float, default=0.0)
    parser.add_argument('--report', help='Number of batches between performance reports',
                        default=100, type=int)

    args = parser.parse_args()

    logger = utils.get_logger('train')
    logger.info('Reading training data')
    train_pairs = readdata.read_snli(args.train)
    logger.info('Reading validation data')
    valid_pairs = readdata.read_snli(args.validation)
    logger.info('Reading word embeddings')
    word_dict, embeddings = readdata.load_text_embeddings(args.embeddings)
    logger.info('Writing word dictionary')
    readdata.write_word_dict(word_dict, args.save)
    logger.debug('Embeddings have shape {}'.format(embeddings.shape))

    logger.info('Converting words to indices')
    max_size1, max_size2 = utils.get_max_sentence_sizes(train_pairs, valid_pairs)
    train_data = utils.generate_dataset(train_pairs, word_dict, max_size1, max_size2)
    valid_data = utils.generate_dataset(valid_pairs, word_dict, max_size1, max_size2)

    # count the NULL token (it is important when there's no alignment for a given word)
    max_size1 += 1
    max_size2 += 1

    msg = '{} sentences have shape {} (firsts) and {} (seconds)'
    logger.debug(msg.format('Training',
                            train_data.sentences1.shape,
                            train_data.sentences2.shape))
    logger.debug(msg.format('Validation',
                            valid_data.sentences1.shape,
                            valid_data.sentences2.shape))

    sess = tf.InteractiveSession()
    logger.info('Creating model')
    model = multimlp.MultiFeedForward(args.num_units, max_size1, max_size2, 3,
                                      embeddings, use_intra_attention=args.use_intra,
                                      training=True, learning_rate=args.rate,
                                      clip_value=args.clip_norm, l2_constant=args.l2)
    sess.run(tf.initialize_all_variables())

    logger.info('Starting training')
    model.train(sess, train_data, valid_data, args.num_epochs, args.batch_size,
                args.dropout, args.save, args.logs, args.report)
