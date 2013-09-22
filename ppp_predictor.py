#!/usr/bin/python

import itertools
import collections
import nose


def elem_next_elem(it):
    """
    returns all the elems, starting from the second one, accompagnied with the
    previous one
    """
    chars, next_chars = itertools.tee(it)
    try:
        next(next_chars)
    except StopIteration:
        return iter([]), iter([])
    else:
        return itertools.izip(chars, next_chars)

class TestElem_PrevElem(object):
    def test_normal(self):
        elem_next = elem_next_elem("abc")
        assert next(elem_next) == ('a', 'b')
        assert next(elem_next) == ('b', 'c')
        try:
            next(elem_next)
        except StopIteration:
            pass
        else:
            raise AssertionError("No StopIteration")
        
    @nose.tools.raises(StopIteration)
    def test_empty_list(self):
        next(elem_next_elem("a"))


def grouper(n, iterable):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))

        if chunk:
            yield chunk
        else:
            return

class TestGrouper(object):
    def test_odd(self):
        assert list(grouper(2, "abcde")) == [("a", "b"), ("c", "d"), ("e",)]

    def test_even(self):
        assert list(grouper(2, "abcd")) == [("a", "b"), ("c", "d")]
        
    def test_empty(self):
        assert list(grouper(2, "")) == []


class MalformedPPPPredictorStream(Exception):
    pass

class PPPPredictor(object):
    
    BITS_PER_PREDICTION_CHUNK = 8 # currently only supported value

    def __init__(self, learning_str):
        count_dict_generator = lambda: collections.defaultdict(lambda: 0)
        next_char_count_by_char = collections.defaultdict(count_dict_generator)
        
        for char, next_char in elem_next_elem(learning_str):
            next_char_count_by_char[char][next_char] += 1
            
        self.predictor = {}
        for char, next_chars in next_char_count_by_char.iteritems():
            best_char = sorted(next_chars, key=lambda x: next_chars.get(x, char))[-1]
            self.predictor[char] = best_char
        

    def compress(self, s):
        strs = collections.deque()

        correct_predictions = self._predict_stream(s)
        for group in grouper(self.BITS_PER_PREDICTION_CHUNK, itertools.izip(correct_predictions, s)):
            preds_group, chars_group = zip(*group) # TODO refactor this boilerplate code

            summary_char = chr(sum(int(pred) << i for i, pred in enumerate(preds_group)))
            compressed_data = ''.join(char for correct_prediction, char in group if not correct_prediction)

            strs.append(summary_char + compressed_data)
        return "".join(strs)

            
    def _predict_stream(self, stream):
        # cannot predict first elem
        correct_predictions = collections.deque([False])
        
        for char, next_char in elem_next_elem(stream):
            correct_predictions.append(next_char == self.predictor.get(char, char))

        return correct_predictions
        

    def uncompress(self, s):
        it = iter(s)

        strs = collections.deque()
        s = None
        while s != "":

            current_char = s and s[-1] or None
            s = "".join(self._uncompress_chunk(current_char, it))
            strs.append(s)

        return "".join(strs)


    def _uncompress_chunk(self, current_char, it):
        prediction_byte = ord(next(it)) # StopIteration ends the generator
        predictions = iter(bool(prediction_byte & (1 << i)) for i in range(self.BITS_PER_PREDICTION_CHUNK))

        for prediction in predictions:

            if prediction is True:
                current_char = self.predictor[current_char]
            else:
                current_char = next(it)

            yield current_char


class TestPPPPredictor(object):
    def setUp(self):
        self.ppppredictor = PPPPredictor("aaabcdef")

        self.pair_3_bytes_compressed = ("aaabcdef", chr(0xf6) + "ab")
        self.pair_incomplete = ("abcdefaaaa", chr(0xBC) + "aba" + chr(0x03)) 

    def test_compress_to_3_bytes(self):
        self.compress(*self.pair_3_bytes_compressed)

    def test_uncompress_to_3_bytes(self):
        self.uncompress(*reversed(self.pair_3_bytes_compressed))

    def test_incomplete_compress(self):
        self.compress(*self.pair_incomplete)

    def test_incomplete_uncompress(self):
        self.uncompress(*reversed(self.pair_incomplete))

    def test_empty_compress(self):
        raise nose.SkipTest()
        self.compress("", "")

    def test_empty_uncompress(self):
        raise nose.SkipTest()
        self.uncompress("", "")

    def compress(self, data, expected):
        result = self.ppppredictor.compress(data)
        assert result == expected, (result,  expected, self.ppppredictor.predictor)
        
    def uncompress(self, data, expected):
        result = "".join(self.ppppredictor.uncompress(data))
        assert result == expected, (result, expected, self.ppppredictor.predictor)


