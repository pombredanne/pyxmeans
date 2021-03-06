#!/usr/bin/env python2.7

import numpy as np
from milk.unsupervised import kmeans
from sklearn.metrics import euclidean_distances
from collections import namedtuple

import logging

KMeansResult = namedtuple("KMeansResult", ("labels", "centroids"))

FORMAT = '[%(asctime)s] %%(levelname)s - (funcName)s:%(lineno)d: %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)

class XMeans(object):
    def __init__(self, data, kmin, kmax):
        self.data = data
        self.kmin = kmin
        self.kmax = kmax

        self.cluster_centers = []
        self._kmeans = None

    def train(self):
        k = self.kmin
        while k <= self.kmax:
            logging.info("Training with k=%d", k)
            self._model = self._fit(k, self.data, self.cluster_centers or None)
            
            centroid_distances = euclidean_distances(self._model.centroids, self._model.centroids)
            centroid_distances += np.diag([np.Infinity] * k)
            centroids_range = centroid_distances.min(axis=-1)

            self.cluster_centers = []
            for i, centroid in enumerate(self._model.centroids):
                logging.info("\tSplitting cluster %d / %d", i+1, len(self._model.centroids))
                direction = np.random.random(centroid.shape)
                vector = direction * (centroids_range[i] / np.sqrt(direction.dot(direction)))

                new_point1 = centroid + vector
                new_point2 = centroid - vector

                logging.info("\t\tRunning secondary kmeans")
                points = self.data[self._model.labels == i]
                test_model = self._fit(2, points, np.asarray([new_point1, new_point2]))

                cluster1 = points[test_model.labels == 0]
                cluster2 = points[test_model.labels == 1]

                bic_parent = XMeans.bic([points], self._model.centroids)
                bic_child = XMeans.bic([cluster1, cluster2], test_model.centroids)
                logging.info("\t\tbic_parent = %f, bic_child = %f", bic_parent, bic_child)
                if bic_child > bic_parent:
                    logging.info("\tUsing children")
                    self.cluster_centers.append(test_model.centroids[0])
                    self.cluster_centers.append(test_model.centroids[1])
                else:
                    logging.info("\tUsing parent")
                    self.cluster_centers.append(centroid)
            if k == len(self.cluster_centers):
                logging.info("Done")
                break
            k = len(self.cluster_centers)

                
    @classmethod
    def bic(cls, clusters, centroids):
        num_points = sum(len(cluster) for cluster in clusters)
        num_dims = clusters[0][0].shape[0]

        log_likelihood = XMeans._loglikelihood(num_points, num_dims, clusters, centroids)
        num_params = XMeans._free_params(len(clusters), num_dims)

        return log_likelihood - num_params / 2.0 * np.log(num_points)


    @classmethod
    def _free_params(cls, num_clusters, num_dims):
        return num_clusters * (num_dims + 1)


    @classmethod
    def _loglikelihood(cls, num_points, num_dims, clusters, centroids):
        ll = 0
        for cluster in clusters:
            fRn = len(cluster)
            t1 = fRn * np.log(fRn)
            t2 = fRn * np.log(num_points)
            variance = XMeans._cluster_variance(num_points, clusters, centroids) or np.nextafter(0, 1)
            t3 = ((fRn * num_dims) / 2.0) * np.log((2.0 * np.pi) * variance)
            t4 = (fRn - 1.0) / 2.0
            ll += t1 - t2 - t3 - t4
        return ll


    @classmethod
    def _cluster_variance(cls, num_points, clusters, centroids):
        s = 0
        denom = float(num_points - len(centroids))
        for cluster, centroid in zip(clusters, centroids):
            distances = euclidean_distances(cluster, centroid)
            s += (distances*distances).sum()
        return s / denom


    def _fit(self, k, data, centroids=None):
        if centroids is not None:
            centroids = np.asarray(centroids, dtype=data.dtype)
        result = kmeans(data, k, centroids=centroids, max_iter=250)
        return KMeansResult(*result)
