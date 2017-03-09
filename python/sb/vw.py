# -*- coding: utf-8 -*-

import sb.util as util
import sb.cwb as cwb
from subprocess import Popen, PIPE
import itertools as it
from functools import wraps
from collections import Counter, namedtuple, OrderedDict
import sys
import json


def predict(model, order, struct, parent, word, out):
    """
    Predict a structural attribute.

    Both model and model.json must exist. See --train.
    """

    index_to_label = json.load(open(model + '.json'))['index_to_label']

    i = util.feed_annotation(out)
    i.next()

    par = util.read_annotation(parent)
    def process_line(s, tok):
        i.send((par[tok], index_to_label[s.rstrip()]))

    def no_target(_):
        return '| '

    args = ['--initial_regressor', model, '--testonly', '-p', '/dev/stdout']

    VW(args, no_target, [(order, struct, parent, word)], process_line)

    try:
        i.send(None)
    except StopIteration:
        pass
    else:
        raise ValueError('?')


def interleave(xs, k):
    """
    Put the elements of xs in k-tuples, with the one same distance
    between consecutive elements in every tuple.

    Does not support infinite xs.

    >>> interleave('abc123', 2)
    [('a', '1'), ('b', '2'), ('c', '3')]
    >>> interleave('abcdABCD1234', 3)
    [('a', 'A', '1'), ('b', 'B', '2'), ('c', 'C', '3'), ('d', 'D', '4')]
    """
    ts = [[] for _ in range(len(xs)/k)]
    ts_iter = it.cycle(ts)
    for x in xs:
        next(ts_iter).append(x)
    return [tuple(t) for t in ts]


def train(files, outprefix):
    """
    Train a model using vowpal wabbit.

    Creates outprefix.model and outprefix.model.json.

    Files is a string of 4*N whitespace-separated elements.
    First N copies of: order,
     then N copies of: annotation_struct,
     then N copies of: parent,
     then N copies of: word.
    """

    modelfile=outprefix + '.model'
    jsonfile=outprefix + '.model.json'

    files = files.split()
    order_struct_parent_word = interleave(files, 4)

    # Look at the structs annotations to get the labels and their distribution:
    _, structs, _, _ = zip(*order_struct_parent_word)
    labels = Counter(label
                     for annotfile in structs
                     for _tok, label in util.read_annotation_iteritems(annotfile))
    N = sum(labels.values())
    k = len(labels)
    label_to_index = {}
    index_to_label = {}
    answer = {}
    for i, (label, occurences) in enumerate(labels.iteritems(), start=1):
        w = float(N)/occurences
        util.log.info('%s: occurences: %s, weight: %s', label, occurences, w)
        answer[label] = ('%s:%s | ' % (i, w)).encode()
        label_to_index[label] = i
        index_to_label[i] = label

    # Train model
    args = [
        '--oaa', str(k),
        '--passes', '10',
        '--cache', '--kill_cache',
        '--bit_precision', '24',
        '--final_regressor', modelfile]
    N_train = VW(args, every(10, invert=True)(answer.get), order_struct_parent_word)

    # Performance evaluation
    predicted = []
    target = []
    @every(10)
    def secret(label):
        target.append(label_to_index[label])
        return b'| '
    def process_line(s, _):
        predicted.append(int(s))
    args = ['--initial_regressor', modelfile, '--testonly', '-p', '/dev/stdout']
    N_eval = VW(args, secret, order_struct_parent_word, process_line=process_line)

    assert len(predicted) == len(target)

    order = list(range(1, 1+k))
    info = dict(
        labels = [index_to_label[i] for i in order],
        index_to_label = index_to_label,
        label_to_index = label_to_index,
        N_train = N_train,
        N_eval = N_eval,
        stats = {index_to_label[i]: p.as_dict()
                 for i, p in
                 multiclass_performance(target, predicted).iteritems()},
        confusion_matrix = confusion_matrix(target, predicted, order))
    with open(jsonfile, 'w') as f:
        json.dump(info, f, sort_keys=True, indent=2)
    util.log.info('Wrote ' + jsonfile)



class Performance(object):
    def __init__(self, TP, TN, FP, FN):
        """
        Performance measures from how many of true and false positives and negatives.

        https://en.wikipedia.org/wiki/Precision_and_recall
        """
        div = lambda x, y: 0.0 if y == 0 else float(x)/float(y)
        harmonic_mean = lambda x, y: div(2*x*y, x+y)
        n = TP + TN + FP + FN
        self.ACC = div(TP + TN, n)
        self.PRE = div(TP, TP + FP)
        self.REC = div(TP, TP + FN)
        self.PRF = harmonic_mean(self.PRE, self.REC)

    def as_dict(self):
        """Performance statistics in a dictionary."""
        keys = 'ACC PRE REC PRF'.split()
        return OrderedDict((k, self.__dict__[k]) for k in keys)

    def __repr__(self):
        perf = ', '.join('%s=%.3f' % kv for kv in self.as_dict().iteritems())
        return "Performance(" + perf + ")"



def binary_performance(target, predicted):
    """
    Standard performance measures on the predictions of a binary classifier.

    >>> p = binary_performance([1,1,1,1,0,0,0,0],
    ...                        [1,1,1,0,0,1,1,0])
    >>> p.ACC == 5/8.0
    True
    >>> p.PRE == 3/5.0
    True
    >>> p.REC == 3/4.0
    True
    """
    d = Counter(zip(target, predicted))
    return Performance(TP = d[1, 1],
                       TN = d[0, 0],
                       FP = d[0, 1],
                       FN = d[1, 0])


def multiclass_performance(target, predicted):
    """
    >>> multiclass_performance([1,1,1,1,2,2,3,3],
    ...                        [1,1,1,2,2,1,1,3])
    ...                                         # doctest: +NORMALIZE_WHITESPACE
    {1: Performance(ACC=0.625, PRE=0.600, REC=0.750, PRF=0.667),
     2: Performance(ACC=0.750, PRE=0.500, REC=0.500, PRF=0.500),
     3: Performance(ACC=0.875, PRE=1.000, REC=0.500, PRF=0.667)}
    """
    return {
        i: binary_performance((t==i for t in target), (p==i for p in predicted))
        for i in nub(it.chain(target, predicted))
    }


def nub(xs):
    """
    All unique elements from xs in order.

    >>> ''.join(nub('apabepa'))
    'apbe'
    >>> import random
    >>> spec = lambda xs: sorted(nub(xs)) == sorted(Counter(xs).keys())
    >>> all(spec(random.sample(range(200), i)) for i in range(100))
    True
    """
    seen = set()
    for x in xs:
        if x not in seen:
            seen.add(x)
            yield x


def confusion_matrix(target, predicted, order):
    """
    Confusion matrix with the target on the y-axis and rows on the x-axis.

    https://en.wikipedia.org/wiki/Confusion_matrix

    >>> confusion_matrix([1,1,1,1,2,2,3,3],
    ...                  [1,1,1,2,2,1,1,3],
    ...                  order=[1,2,3])         # doctest: +NORMALIZE_WHITESPACE
    [[3, 1, 0],
     [1, 1, 0],
     [1, 0, 1]]
    """

    matrix = Counter(zip(target, predicted))
    return [[ matrix.get((t, p), 0) for p in order ] for t in order]



def every(sep, invert=False):
    """
    Every sep time the function is called, execute it, otherwise return None.

    The function is hard-coded to be unary.
    To make it more general change arg to *args, **kwargs.

    >>> @every(3)
    ... def greet(person):
    ...     return 'Hello ' + person
    >>> greet('Dan')
    >>> greet('Malin')
    >>> greet('Maria')
    'Hello Maria'
    >>> greet('Martin')
    >>> greet('Anne')
    >>> greet('Jonatan')
    'Hello Jonatan'

    >>> @every(3, invert=True)
    ... def greet(person):
    ...     return 'Hello ' + person
    >>> greet('Dan')
    'Hello Dan'
    >>> greet('Malin')
    'Hello Malin'
    >>> greet('Maria')
    >>> greet('Martin')
    'Hello Martin'
    >>> greet('Anne')
    'Hello Anne'
    >>> greet('Jonatan')
    """
    def decorator(func):
        x = [0]
        @wraps(func)
        def do(arg):
            x[0] += 1
            last = x[0] == sep
            if last:
                x[0] = 0
            if last != invert:
                return func(arg)
            else:
                return None
        return do
    return decorator


def VW(args, target_for_example, order_struct_parent_word, process_line=None):
    stdout = PIPE if process_line else sys.stdout
    vw = Popen(['vw'] + args, stdin=PIPE, stdout=stdout, stderr=sys.stderr)
    util.log.info('Running: vw ' + ' '.join(args))
    stdin = vw.stdin

    X = 0
    for order, struct, parent, word in order_struct_parent_word:
        x = 0
        util.log.info("Processing %s %s %s", struct, parent, word)
        tokens, vrt = cwb.tokens_and_vrt(order, [(struct, parent)], [word])
        for (label, last_tok), words in \
                cwb.vrt_iterate(tokens, vrt, project_struct=lambda *xs: xs):
            line = target_for_example(label)
            if line:
                for word in words:
                    line += cwb.fmt(vw_features.normalize(word)) + b' '
                # line have values like '2:4.9882 | apa bepa cepa' when training
                stdin.write(line + b'\n')
                x += 1
                if process_line:
                    stdin.flush()
                    process_line(vw.stdout.readline(), last_tok) # handle predicted value
        util.log.info("Examples from %s: %s", struct, x)
        X += x
    util.log.info("Total examples: %s", X)

    stdin.close()
    vw.wait()
    return X


class vw_features(object):
    """Normalization for Vowpal Wabbit features (vw)."""
    escape_symbols = [
        # Replace digits with X
         (unicode(x), u'X') for x in range(10)
        ] + map(tuple, (
            # Vowpal Wabbit needs these to be escaped:
            u' S', # separates features
            u'|I', # separates namespaces
            u':C'  # separates feature and its value
        ))
    escape_table={ord(k): v for k, v in escape_symbols}

    @staticmethod
    def normalize(s):
        u"""
        >>> print(vw_features.normalize(u'VW | abcåäö:123'))
        vwSISabcåäöCXXX
        """
        return s.lower().translate(vw_features.escape_table)


def triangulate(xs):
    """
    All initial segments of xs, concatenated.

    >>> ''.join(triangulate('abc'))
    'aababc'
    >>> ''.join(triangulate('1234'))
    '1121231234'
    >>> list(triangulate([]))
    []
    """
    for i, _ in enumerate(xs):
        for x in xs[:i+1]:
            yield x


def make_testdata(corpus_desc='abcd abcd dcba cbad', docs=1000):
    """
    Write amazing test data on stdout.
    """
    import random
    n_docs = int(docs)
    make = lambda s: (s, triangulate(s))
    corpuses = [(s, tuple(triangulate(s))) for s in corpus_desc.split()]
    for _ in range(n_docs):
        corpus, freq = random.choice(corpuses)
        print('<text label="' + corpus + '">')
        n_words = random.randint(12, 39)
        print(' '.join(random.choice(freq) for _ in range(n_words)))
        print('</text>')


if __name__ == '__main__':
    import doctest
    util.run.main(train=train, predict=predict, make_testdata=make_testdata,
                  test=lambda verbose=False: doctest.testmod(verbose=verbose))
