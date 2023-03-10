# -*- coding: utf-8 -*-

import os
import cv2
import dlib
import numpy as np
import argparse

here = os.path.dirname(os.path.abspath(__file__))

models_folder_path = os.path.join(here, 'models')  # model dir
faces_folder_path = os.path.join(here, 'faces')  # test face dir
predictor_path = os.path.join(models_folder_path, 'shape_predictor_68_face_landmarks.dat')  # model path


detector = dlib.get_frontal_face_detector()  # dlib face detector
predictor = dlib.shape_predictor(predictor_path)  # dlib landmark detector


def get_image_size(image):
    """
    """
    image_size = (image.shape[0], image.shape[1])
    return image_size


def get_face_landmarks(image, face_detector, shape_predictor):
    """    
    :param image: image
    :param face_detector: dlib.get_frontal_face_detector
    :param shape_predictor: dlib.shape_predictor
    :return: np.array([[],[]]), 68 points
    """
    dets = face_detector(image, 1)
    num_faces = len(dets)
    if num_faces == 0:
        print("Sorry, there were no faces found.")
        return None
    shape = shape_predictor(image, dets[0])
    face_landmarks = np.array([[p.x, p.y] for p in shape.parts()])
    return face_landmarks


def get_face_mask(image_size, face_landmarks):
    """    
    :param image_size:
    :param face_landmarks: 68 landmark points
    :return: image_mask, mask image
    """
    mask = np.zeros(image_size, dtype=np.uint8)
    points = np.concatenate([face_landmarks[0:16], face_landmarks[26:17:-1]])
    cv2.fillPoly(img=mask, pts=[points], color=255)

    # mask = np.zeros(image_size, dtype=np.uint8)
    # points = cv2.convexHull(face_landmarks)  # 凸包
    # cv2.fillConvexPoly(mask, points, color=255)
    return mask


def get_affine_image(image1, image2, face_landmarks1, face_landmarks2):
    """    
    """
    three_points_index = [18, 8, 25]
    M = cv2.getAffineTransform(face_landmarks1[three_points_index].astype(np.float32),
                               face_landmarks2[three_points_index].astype(np.float32))
    dsize = (image2.shape[1], image2.shape[0])
    affine_image = cv2.warpAffine(image1, M, dsize)
    return affine_image.astype(np.uint8)


def get_mask_center_point(image_mask):
    """
    """
    image_mask_index = np.argwhere(image_mask > 0)
    miny, minx = np.min(image_mask_index, axis=0)
    maxy, maxx = np.max(image_mask_index, axis=0)
    center_point = ((maxx + minx) // 2, (maxy + miny) // 2)
    return center_point


def get_mask_union(mask1, mask2):
    """
    """
    mask = np.min([mask1, mask2], axis=0)  # 
    mask = ((cv2.blur(mask, (5, 5)) == 255) * 255).astype(np.uint8)  #
    mask = cv2.blur(mask, (3, 3)).astype(np.uint8)  #
    return mask


def skin_color_adjustment(im1, im2, mask=None):
    """
    """
    if mask is None:
        im1_ksize = 55
        im2_ksize = 55
        im1_factor = cv2.GaussianBlur(im1, (im1_ksize, im1_ksize), 0).astype(np.float)
        im2_factor = cv2.GaussianBlur(im2, (im2_ksize, im2_ksize), 0).astype(np.float)
    else:
        im1_face_image = cv2.bitwise_and(im1, im1, mask=mask)
        im2_face_image = cv2.bitwise_and(im2, im2, mask=mask)
        im1_factor = np.mean(im1_face_image, axis=(0, 1))
        im2_factor = np.mean(im2_face_image, axis=(0, 1))

    im1 = np.clip((im1.astype(np.float) * im2_factor / np.clip(im1_factor, 1e-6, None)), 0, 255).astype(np.uint8)
    return im1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="faces/3.jpg", help="source face file path")
    parser.add_argument("--drive", default="faces/4.jpg", help="reference face file path")
    parser.add_argument("--outpath", default="faces/out.jpg", help="output file path")
    parser.add_argument("--type", default=0, help="face swap type")

    args = parser.parse_args()

    image_face_path = args.source
    outpath = args.outpath

    im1 = cv2.imread(image_face_path)  # face_image
    im1 = cv2.resize(im1, (600, im1.shape[0] * 600 // im1.shape[1]))
    landmarks1 = get_face_landmarks(im1, detector, predictor)  # 68_face_landmarks
    if landmarks1 is None:
        print('{}:can not find face'.format(image_face_path))
        exit(1)
    im1_size = get_image_size(im1)  # 
    im1_mask = get_face_mask(im1_size, landmarks1)  # 


    im2 = cv2.imread(args.drive)

    landmarks2 = get_face_landmarks(im2, detector, predictor)  # 68_face_landmarks
    if landmarks2 is not None:
        im2_size = get_image_size(im2)  # 
        im2_mask = get_face_mask(im2_size, landmarks2)  # 

        affine_im1 = get_affine_image(im1, im2, landmarks1, landmarks2)  # im1
        affine_im1_mask = get_affine_image(im1_mask, im2, landmarks1, landmarks2)  # im1

        union_mask = get_mask_union(im2_mask, affine_im1_mask)  #

        # affine_im1_face_image = cv2.bitwise_and(affine_im1, affine_im1, mask=union_mask)  # im1
        # im2_face_image = cv2.bitwise_and(im2, im2, mask=union_mask)  # im2
        # cv2.imshow('affine_im1_face_image', affine_im1_face_image)
        # cv2.imshow('im2_face_image', im2_face_image)

        affine_im1 = skin_color_adjustment(affine_im1, im2, mask=union_mask)  #
        point = get_mask_center_point(affine_im1_mask)  # im1
        seamless_im = cv2.seamlessClone(affine_im1, im2, mask=union_mask, p=point, flags=cv2.NORMAL_CLONE)  #

        # cv2.imshow('affine_im1', affine_im1)
        # cv2.imshow('im2', im2)        
        cv2.imwrite(outpath, seamless_im)
    else:
        pass

    


if __name__ == '__main__':
    main()
