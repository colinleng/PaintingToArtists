import os
import argparse
import sys
import pickle
import cv2
import numpy as np

from project_types import *
from images import *

from ColorHistogram import ColorHistogram
from BagOfWords import BagOfWords
from MultiSVM import MultiSVM
from structuredSVM import StructuredSVM

def get_args():

    parser = argparse.ArgumentParser(description="This is the main file for running different types of algorithms.")

    parser.add_argument("--folder", type=str,
        help="The folder to use for extracting features.")
    parser.add_argument("--mode", type=str, required=True, choices=["feature", "train", "test"],
                        help="Operating mode: feature extraction, train or test.")
    parser.add_argument("--feature-file", type=str,
                        help="The name of the file containing feature converter/ instance creator")
    parser.add_argument("--model-file", type=str,
                        help="The name of the model file to create/load.")
    parser.add_argument("--predictions-file", type=str, help="The predictions file to create.")
    parser.add_argument("--feature-algorithm", type=str, help="The name of the algorithm for training.")
    parser.add_argument("--training-algorithm", type=str, help="The name of the algorithm for training.")

    args = parser.parse_args()
    check_args(args)

    return args


def check_args(args):
    if args.mode.lower() == "feature":
        if args.folder is None:
            raise Exception("--folder (folder with data) should be specified in mode \"feature\"")
        if args.feature_algorithm is None:
            raise Exception("--algorithm (feature extraction algorithm) should be specified in mode \"feature\"")
        if args.feature_file is None:
            raise Exception("--feature-file (save features) should be specified in mode \"feature\"")
        if args.feature_algorithm is None:
            raise Exception("--feature-algorithm should be specified in mode \"feature\"")
    elif args.mode.lower() == "train":
        if args.folder is None and args.feature_file is None:
            raise Exception("--feature-file or --folder (load training features) should be specified in mode \"train\"")
        if args.folder is not None and args.feature_algorithm is None:
            raise Exception("--feature-algorithm should be specified in mode \"train\" when given folder")
        if args.feature_file is not None and not os.path.exists(args.feature_file):
            raise Exception("feature file specified by --feature-file does not exist.")
        if args.training_algorithm is None:
            raise Exception("--training-algorithm should be specified in mode \"train\"")
        if args.model_file is None:
            raise Exception("--model-file should be specified in mode \"train\"")
    else:
        if args.folder is None and args.feature_file is None:
            raise Exception("--feature-file or --folder (load training features) should be specified in mode \"train\"")
        if args.folder is not None and args.feature_algorithm is None:
            raise Exception("--feature-algorithm should be specified in mode \"test\" when given folder")
        if args.feature_file is not None and not os.path.exists(args.feature_file):
            raise Exception("feature file specified by --feature-file does not exist.")
        if args.predictions_file is None:
            raise Exception("--prediction-file should be specified in mode \"test\"")
        if args.model_file is None:
            raise Exception("--model-file should be specified in mode \"test\"")
        if not os.path.exists(args.model_file):
            raise Exception("model file specified by --model-file does not exist.")


def get_files(folder_name, algorithm, args):

    foldersTmp = os.listdir(folder_name)
    folders = []
    for folder in foldersTmp:
        if folder[0] == '.':
            continue
        folders.append(folder)

    imgs = []
    for folder in folders:
        path = folder_name + folder + '/'
        files = os.listdir(path)
        for file_str in files:
            complete_file_str = str((os.path.join(path, file_str)))
            if os.path.isfile(complete_file_str) and (complete_file_str.endswith('.jpg') or complete_file_str.endswith('.JPG')):
                imgs.append((os.path.join(path, file_str), folder))

    return imgs


# load instances from filename
def load_data(filename):
    instances = None
    try:
        with open(filename, 'rb') as reader:
            instances = pickle.load(reader)
    except IOError:
        raise Exception("Exception while reading the model file.")
    except pickle.PickleError:
        raise Exception("Exception while loading pickle.")
    return instances


# print in predictions_file both correct answer and wrong answer
def write_predictions(predictor, feature_converter, predictions_file):
    labels = predictor.predict(feature_converter)
    try:
        with open(predictions_file, 'w') as writer:
            for i in range(len(labels)):
                label = labels[i]
                instance = feature_converter.get_testing_instance(i)
        
                writer.write(str(label))
                writer.write(' ')
                writer.write(instance.get_label())
                writer.write('\n')
    except IOError:
        raise Exception("Exception while opening/writing file for writing predicted labels: " + predictions_file)


def get_instance_converter(algorithm, args):
    if algorithm == "color":
        return ColorHistogram()
    elif algorithm == "bow":
        return BagOfWords()      
    return None

# train algorithm on instances
def train(algorithm, args):
    if algorithm == "mc_svm":
        # create multiclass SVM model
        return MultiSVM()
    elif algorithm == "struct_svm":
        return StructuredSVM()
    elif algorithm == "nn":
        # train a neural network
        return None
    return None


def main():
    args = get_args()

    mode = args.mode.lower()
    if mode == "feature":

        # args.folder is the folder where training data and testing data is, with specific
        # directory structure
        feature_converter = get_instance_converter(args.feature_algorithm, args)
        training_files = get_files(args.folder + '/train/', args.feature_algorithm, args)
        testing_files = get_files(args.folder + '/test/', args.feature_algorithm, args)
        feature_converter.createTrainingInstances(training_files)
        feature_converter.createTestingInstances(testing_files)

        try:
            with open(args.feature_file, 'wb') as writer:
                pickle.dump(feature_converter, writer)
        except IOError:
            raise Exception("Exception while writing to the model file.")        
        except pickle.PickleError:
            raise Exception("Exception while dumping pickle.")

    elif mode == "train":
        # Load the training data.
        if args.feature_file is not None:
            feature_converter = load_data(args.feature_file)
        else:
            feature_converter = get_instance_converter(args.feature_algorithm, args)
            training_files = get_files(args.folder + '/train/', args.feature_algorithm, args)
            feature_converter.createTrainingInstances(training_files)

        # train some model
        predictor = train(args.training_algorithm, args)
        predictor.train(feature_converter)
        # save the model
        try:
            with open(args.model_file, 'wb') as writer:
                pickle.dump(predictor, writer)
        except IOError:
            raise Exception("Exception while writing to the model file.")        
        except pickle.PickleError:
            raise Exception("Exception while dumping pickle.")
            
    elif mode == "test":
        # Load the test data.
        if args.feature_file is not None:
            feature_converter = load_data(args.feature_file)
        else:
            feature_converter = get_instance_converter(args.feature_algorithm, args)
            testing_files = get_files(args.folder + '/test/', args.feature_algorithm, args)
            feature_converter.createTestingInstances(testing_files)

        predictor = None
        # Load the model.
        try:
            with open(args.model_file, 'rb') as reader:
                predictor = pickle.load(reader)
        except IOError:
            raise Exception("Exception while reading the model file.")
        except pickle.PickleError:
            raise Exception("Exception while loading pickle.")
            
        # use predictor on instances, save in args.predictions_file
        write_predictions(predictor, feature_converter, args.predictions_file)
    else:
        raise Exception("Unrecognized mode.")

if __name__ == "__main__":
    main()
