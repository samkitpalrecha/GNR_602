# -*- coding: utf-8 -*-
"""ultrafinalgnrwithinterface.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1LJ63iK0Rcnys6CvAFm7rnjw0mj4bV23l
"""

import argparse
import cv2
from collections import Counter
import numpy as np
import time
import os
import skimage.morphology
!pip install gradio
import gradio as gr

# Function to perform KMeans clustering
def custom_kmeans(data, n_clusters):
    # Initialize centroids randomly
    centroids = data[np.random.choice(data.shape[0], n_clusters, replace=False)]
    prev_assignments = None

    while True:
        # Assign each point to the nearest centroid
        distances = np.linalg.norm(data[:, np.newaxis] - centroids, axis=2)
        assignments = np.argmin(distances, axis=1)

        # If no points changed clusters, break
        if np.array_equal(assignments, prev_assignments):
            break

        # Update centroids
        for i in range(n_clusters):
            cluster_points = data[assignments == i]
            if len(cluster_points) > 0:
                centroids[i] = np.mean(cluster_points, axis=0)

        prev_assignments = assignments

    return assignments

# PCA implementation
def custom_pca(data):
    # Calculate mean vector
    mean_vec = np.mean(data, axis=0)
    # Mean normalization
    data_normalized = data - mean_vec
    # Calculate covariance matrix
    cov_matrix = np.cov(data_normalized.T)
    # Perform eigendecomposition
    eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)
    # Sort eigenvectors based on eigenvalues
    sorted_indices = np.argsort(eigenvalues)[::-1]
    sorted_eigenvalues = eigenvalues[sorted_indices]
    sorted_eigenvectors = eigenvectors[:, sorted_indices]
    # Choose components
    components = sorted_eigenvectors[:, :3]  # Assuming 3 components
    return components, mean_vec

# Function to extract vector set
def find_vector_set(diff_image, new_size):
    i = 0
    j = 0
    vector_set = np.zeros((int(new_size[0] * new_size[1] / 25), 25))
    while i < vector_set.shape[0]:
        while j < new_size[1]:
            k = 0
            while k < new_size[0]:
                # Extracting features from blocks
                block = diff_image[j:j+5, k:k+5]
                feature = block.ravel()
                vector_set[i, :] = feature
                k = k + 5
            j = j + 5
        i = i + 1

    # Calculate mean vector
    mean_vec = np.mean(vector_set, axis=0)
    # Mean normalization
    vector_set = vector_set - mean_vec
    return vector_set, mean_vec

# Function to find Feature Vector Space
def find_FVS(EVS, diff_image, mean_vec, new):
    i = 2
    feature_vector_set = []

    while i < new[1] - 2:
        j = 2
        while j < new[0] - 2:
            # Extracting features from blocks
            block = diff_image[i-2:i+3, j-2:j+3]
            feature = block.flatten()
            feature_vector_set.append(feature)
            j = j + 1
        i = i + 1

    # Calculate mean vector for broadcasting
    mean_vec_broadcasted = np.mean(feature_vector_set, axis=0)

    # Perform mean normalization
    feature_vector_set -= mean_vec_broadcasted

    # Project features onto eigenvectors
    FVS = np.dot(feature_vector_set, EVS)

    print("[INFO] Feature vector space size", FVS.shape)
    return FVS

# Function for clustering
def clustering(FVS, components, new):
    output = custom_kmeans(FVS, components)
    count = Counter(output)

    least_index = min(count, key=count.get)
    change_map = np.reshape(output, (new[1] - 4, new[0] - 4))
    return least_index, change_map

# Function to perform change detection
def detect_changes(image1_path, image2_path):
    # Read input images
    image1 = cv2.imread(image1_path)
    image2 = cv2.imread(image2_path)

    # Resize images
    new_size = np.asarray(image1.shape) / 5
    new_size = new_size.astype(int) * 5
    image1 = cv2.resize(image1, (new_size[0], new_size[1])).astype(int)
    image2 = cv2.resize(image2, (new_size[0], new_size[1])).astype(int)

    # Compute difference image
    diff_image = abs(image1 - image2)
    diff_image = diff_image[:, :, 1]  # taking only green channel difference

    # Perform PCA
    vector_set, mean_vec = find_vector_set(diff_image, new_size)
    EVS, mean_vec = custom_pca(vector_set)

    # Build Feature Vector Space
    FVS = find_FVS(EVS, diff_image, mean_vec, new_size)
    components = 3

    # Perform clustering
    least_index, change_map = clustering(FVS, components, new_size)

    # Threshold the change map
    change_map[change_map == least_index] = 255
    change_map[change_map != 255] = 0
    change_map = change_map.astype(np.uint8)

    # Extract image filenames without directory paths
    image1_filename = os.path.basename(image1_path)
    image2_filename = os.path.basename(image2_path)

    # Save Change Map
    change_map_filename = "ChangeMap_" + os.path.splitext(image1_filename)[0] + ".jpg"
    change_map_path = os.path.join(change_map_filename)
    cv2.imwrite(change_map_path, change_map)

    # Load the change map image
    change_map_image = cv2.imread(change_map_path)

    return change_map_image  # Return the change map image


# Gradio interface
iface = gr.Interface(fn=detect_changes,
                     inputs=["file", "file"],
                     outputs="image",
                     title="Change Detection in Satellite Images",
                     description="Upload two multi-temporal satellite images to detect changes.")
iface.launch(share=True)