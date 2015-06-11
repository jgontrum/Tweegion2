#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Johannes Gontrum <gontrum@uni-potsdam.de>'

import sys
import math
from Evaluation import CorpusUserEvaluator
import cPickle as pickle
from Evaluation import Weighting
from WeightLearning import AvgDistance

load_pickled = None
if len(sys.argv) > 3:
    load_pickled = sys.argv[1]
    load_clusters = sys.argv[2]
else:
    sys.exit(1)

token_to_data = pickle.load(open(load_pickled, 'rb')) #< ((lon, lat), variance, count)
clusters = pickle.load(open(load_clusters, 'rb')) #<
user_to_midpoint = pickle.load(open(sys.argv[3], 'rb'))

""" EVALUATE """
"""
weights = None
try:
    weights = pickle.load(open("AvgDistanceWeights.pickle", 'rb'))
except:
    weights = AvgDistance.createWeightedList(token_to_data)
    pickle.dump(weights, open("AvgDistanceWeights.pickle", 'wb'))

evaluator_list = Weighting.WeightListEvaluator(weights, "AvgDistance")
"""

dev_corpus = CorpusUserEvaluator.CorpusEvaluator(corpus='DEV')
dev_corpus.setData(token_to_data, clusters, null=False)
dev_corpus.setDistanceThreshold(200)
dev_corpus.setUserToMidpoint(user_to_midpoint)
dev_corpus.setUserToTokenData(pickle.load(open(sys.argv[4], 'rb')))
dev_corpus.setUserToTweets(pickle.load(open(sys.argv[5], 'rb')))

print "Data read!"
# evaluator = Weighting.NegLogVarianceEvaluator() #InversedVarianceEvaluator2(pow=-1.0)
evaluator = Weighting.TopTokensEvaluator(Weighting.InversedVarianceEvaluator(),3);
dev_corpus.setEvaluator(evaluator)

thresholds = [  1] #, 0.0017138, 0.0014019, 0.000594, 0.0003886 ] #1, 0.0017138, 0.0014019, 0.000594,
for threshold in thresholds:
    dev_corpus.setVarianceThreshold(threshold)
    print ""
    print threshold
    print dev_corpus.evaluateCorpus()
