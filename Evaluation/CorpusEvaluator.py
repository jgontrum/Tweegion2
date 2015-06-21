#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Johannes Gontrum <gontrum@uni-potsdam.de>'

import random
import os
from Wrapper import MySQLConnection
from Wrapper import MapFunctions
import matplotlib.pyplot as plt
from Evaluation import EvaluationFunctions
import cPickle as pickle
import base64
from random import randint
from tabulate import tabulate
import numpy as np
import itertools
import math
from scipy.stats import multivariate_normal

class CorpusEvaluator:
    def __init__(self, signature=None, clusters=None, corpus='DEV'):
        self.tweets = []        # list of tokenised tweets
        self.location = []      # list of lat, lan tuples
        self.n = 0              # The size of the corpus
        self.clusters = None    # List of centroid coordinates
        self.variance_threshold = 0
        self.distance_threshold = 0
        self.draw = False       # Toggle weather each tweet should be saved to a PNG file
        self.evaluator = None   # Creates the weights for the tokens in a tweet
        self.null = False       # Test 0-hypothesis
        self.signature = signature
        self.clusters = clusters
        self.users = []

        # Load corpus from database:
        database = MySQLConnection.MySQLConnectionWrapper(basedir=os.getcwd() + "/", corpus=corpus)
        user_to_tweets = {}

        for tokens, lat, lon, user in database.getRows("`tokenised_low`, `lat`, `long`, `user_id`"):
            self.tweets.append(tokens.split())
            self.users .append(user)
            user_to_tweets.setdefault(user, []).append(tokens.split())
            self.location.append((lon, lat))
        self.n = len(self.tweets)
        assert len(self.tweets) == len(self.location)

        # Lookup tokendata
        self.token_data = {}

        # collect ids
        ids = []
        for tweet in self.tweets:
            for token in EvaluationFunctions.getCoOccurrences(tweet):
                ids.append(signature.add(token))
        ids = set(ids)

        # Get data from database
        token_db = MySQLConnection.MySQLConnectionWrapper(basedir=os.getcwd() + "/", corpus="TOKENDATA")
        for token_id, lon, lat, variance, count, b64function \
            in token_db.getTokenInfo(ids, columns= \
            "`id`, `long`, `lat`, `variance`, `count`, `function`"):

                    function = pickle.loads(base64.b64decode(b64function))
                    self.token_data[token_id] = {"location" : (lon, lat),
                                           "variance" : variance,
                                           "count" : count,
                                           "function" : function}
        # Combine all user tweets
        # for user, tweets in user_to_tweets.iteritems():
        #     tokens = []
        #     for t in tweets:
        #         tokens += t
        #     for i in range(self.n):
        #         if self.users[i] == user:
        #             self.tweets[i] = tokens

    def setEvaluator(self, evaluator):
        self.evaluator = evaluator

    def setVarianceThreshold(self, threshold):
        self.variance_threshold = threshold

    def setDistanceThreshold(self, threshold):
        self.distance_threshold = threshold

    # Takes a list of tokens and a location.
    # Calculates the position of the tweet and compares it to the actual
    # position.
    def evaluateTweet(self, tokens, location):
        token_data_here = []

        valid = 0
        if self.draw:
            basemap = MapFunctions.prepareMap()

        text_pos = 1890000
        
        # Look up the data for each token in the tweet
        for token in EvaluationFunctions.getCoOccurrences(tokens):
            token_id =  self.signature.add(token)
            if token_id not in self.token_data:
                if False: #self.draw:
                    plt.text(10000, text_pos, token.decode('utf8', 'ignore') + ' | (fail)', color='grey', fontsize=6)
                    text_pos -= 42000
                continue
            data = self.token_data[token_id]
            variance = data['variance']
            count = data['count']
            lon, lat = data["location"]
            if variance < self.variance_threshold: # and count > 10:
                valid += 1
                if self.draw:
                    #plt.text(10000, text_pos, token.decode('utf8', 'ignore') + ' | ' + str(round(variance,1)) + ' | ' + str(count), color='black', fontsize=6)
                    text_pos -= 42000
                    current_color = EvaluationFunctions.getColorForValue(variance)
                    basemap.plot(lon, lat, 'o', latlon=True, markeredgecolor=current_color, color=current_color, markersize=EvaluationFunctions.getSizeForValue(count), alpha=0.7)
                token_data_here.append((token, variance, count, data["location"], data["function"]))

            else:
                if self.draw:
                    #plt.text(10000, text_pos,   token.decode('utf8', 'ignore') + ' | ' + str(round(variance,1)) + ' | ' + str(count),color='grey', fontsize=6)
                    text_pos -= 40000
                    current_color = 'gray'
                    basemap.plot(lon, lat, 'o', latlon=True, markeredgecolor=current_color, color=current_color, markersize=EvaluationFunctions.getSizeForValue(count), alpha=0.1)

        if valid == 0:
            plt.clf()
            return None

        # mcvlist = [(mean, covar, token) for (token, variance, count, coordinates, mean, covar) in token_data_here ]
        # for (mean1, covar1, token1), (mean2, covar2, token2) in itertools.combinations(mcvlist, 2):
        #     # get x0:
        #     x0 = (mean1 + mean2) / 2
        #     print token1, token2
        #     print mean1
        #     print mean2
        #     print EvaluationFunctions.get_crossing(mean1, covar1, mean2, covar2,x0)
        #     print "---"

        # Find initial guess by estimating a midpoint
        x0 = np.array([51,10])
        functions = []
        tokens = []
        loc = []
        variances = []
        for (token, variance, count, coordinates, function) in token_data_here:
            functions.append(function)
            tokens.append(token)
            variances.append(variance)
            loc.append(coordinates)

        if len(functions) > 0:
            ((lon_score, lat_score), score) = EvaluationFunctions.get_combinations(functions, x0)
        else: 
            return None
        
        distance = EvaluationFunctions.getDistance(lon_score, lat_score, location[0], location[1])

        if self.draw:
            basemap.plot(location[0], location[1], '^', mfc='none' , markeredgecolor='black', latlon=True, alpha=1)
            basemap.plot(lon_score, lat_score, 'v',  mfc='none',  markeredgecolor='black', latlon=True, alpha=1)
           
            plt.text(10000,10000,'Distance: '+ str(round(distance,1)) + 'km')
            plt.text(10000,80000, 'Threshold: ' + str(self.variance_threshold))
            plt.savefig('img/tweet_' + str(self.variance_threshold) + "_" + str(self.i) + ".png", format='png')
            plt.clf()
        
        #pickle.dump((functions,loc, location, x0, (lon_score, lat_score), distance,score,tokens,variances), open("tweet_" + str(self.i) + "_" + str(self.variance_threshold) +".pickle", "wb"))

        return (lon_score, lat_score, location[0], location[1], distance)


    def evaluateCorpus(self, printmsg=False):
        distances = []
        valids = 0
        invalids = 0

        distance_matches = 0
        distance_mismatches = 0

        cluster_matches = 0
        cluster_mismatches = 0
        
        n = len(self.clusters)
        real_to_calc_matches = [[0 for x in range(n+1)] for x in range(n)] 
        for i in range(n):
            real_to_calc_matches[i][0] = i

       # self.n = 3
        for self.i in range(0,self.n):
            values = self.evaluateTweet(self.tweets[self.i], self.location[self.i])
            if values is None:
                invalids += 1
            else:
                lon_calculated, lat_calculated, lon_real, lat_real, distance = values
                distances.append(distance)

                if EvaluationFunctions.evaluateDistance(distance, self.distance_threshold):
                    distance_matches += 1
                else:
                    distance_mismatches += 1

                if EvaluationFunctions.evaluateCluster(lon_calculated, lat_calculated, lon_real, lat_real, self.clusters, real_to_calc_matches):
                    cluster_matches += 1
                else:
                    cluster_mismatches += 1

                valids += 1

        distances_np = np.asarray(distances, dtype=float)
        if printmsg:
            print 'valid: ', valids, 'invalid: ', invalids

            print 'distance_match: ', distance_matches, 'distance_mismatches: ', distance_mismatches
            if distance_matches + distance_mismatches > 0:
                print 'distance_ratio: ', str(float(distance_matches) / (distance_matches + distance_mismatches))

            print 'cluster_matches: ', cluster_matches, 'cluster_mismatches: ', cluster_mismatches
            if cluster_matches + cluster_mismatches > 0:
                print 'cluster_ratio: ', str(float(cluster_matches) / (cluster_matches + cluster_mismatches))

        # print "not used: ", self.tmpscore
        #print tabulate(real_to_calc_matches, tablefmt="latex",headers=range(n))
        
        #print tabulate(EvaluationFunctions.transformStatistice(real_to_calc_matches), tablefmt="latex",headers=range(n))

        if valids > 0:
            return  (np.mean(distances_np), np.median(distances_np), float(cluster_matches) / (cluster_matches + cluster_mismatches))
        else:
            return  (float('inf'), float('inf'), float('inf'))

