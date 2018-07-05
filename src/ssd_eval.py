# -*- coding: utf-8 -*-
# Author:  08/25/2016

"""SqueezeDet Demo.

In image detection mode, for a given image, detect objects and draw bounding
boxes around them. In video detection mode, perform real-time detection on the
video stream.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import cv2
import time
import sys
import os
import glob

import numpy as np
import tensorflow as tf
from struct import *
from config import *
#from train import _draw_box
from nets import *
from utils.util import clip_box
import fileinput

FLAGS = tf.app.flags.FLAGS

#./data/model_checkpoints/squeezeDet/model.ckpt-87000
tf.app.flags.DEFINE_string(
    'checkpoint', './SqueezeDet/model_save/model.ckpt-99000',
    """Path to the model parameter file.""")
    
tf.app.flags.DEFINE_string(
    'images_path', 'data/VKITTI/training/image_2',
    """images path.""")

tf.app.flags.DEFINE_string(
    'labels_dir', 'data/VKITTI/training/label_2',
    """labels_file.""")

tf.app.flags.DEFINE_string(
    'eval_file', 'data/VKITTI/ImageSets/val.txt',
    """labels_file.""")
    
tf.app.flags.DEFINE_string(
    'eval_out_dir', './logs/SSD/eval_val', 
    """eval_out_file.""")
tf.app.flags.DEFINE_string('net', 'squeezeDet',
                           """Neural net architecture. """)
tf.app.flags.DEFINE_string('gpu', '0', """gpu id.""")

def ssd_filter_variables(all_variables):
    left_variables = []

    filter_key = ['Momentum','iou','global_step']
    for v in all_variables:
      print ("name:",v.name)

      isexist = False
      for i in range(0,len(filter_key)):
        if filter_key[i] in v.name:
            isexist = True
            break
      if isexist == True:
        continue
        
      left_variables += [v]

    return left_variables

def save_eval_res(mc,image_filename,height,width,final_boxes,final_probs,final_class):
    clases = mc.CLASS_NAMES

    for i,box in enumerate(final_boxes):
      box_clip = clip_box(box,height,width)
      score = final_probs[i]
      cls = final_class[i]
      if cls == 0:
        continue

      #print ('cls:',cls)
      cls_filename = os.path.join(FLAGS.eval_out_dir,'results_{}.txt'.format(cls))
      
      filename = image_filename.split('.')[0]
      with open(cls_filename,'a+') as f:
        f.write('{} {} {} {} {} {}\n'.format(filename,score,
                  box_clip[0],box_clip[1],box_clip[2],box_clip[3]))
        
      #raw_input('pause')

    
def eval():
    """Detect image."""

    with tf.Graph().as_default():

        if FLAGS.net == 'SSD':
            mc = vkitti_SSD_config()
            mc.BATCH_SIZE = 1
            mc.LOAD_PRETRAINED_MODEL = False
            mc.is_training = False
            model = SSDNet(mc,FLAGS.gpu)
            saver = tf.train.Saver(tf.global_variables())
            
        elif FLAGS.net == 'SSD_Mobilenet':
            mc = vkitti_SSD_Mobilenet_config()
            mc.BATCH_SIZE = 1
            mc.LOAD_PRETRAINED_MODEL = False
            mc.is_training = False
            model = SSD_Mobilenet(mc,FLAGS.gpu)
            saver = tf.train.Saver(tf.global_variables())
          
        else:
            print ('No this net type!')
            return
        
        with tf.Session(config=tf.ConfigProto(allow_soft_placement=True)) as sess:
            init = tf.global_variables_initializer()
            sess.run(init)
            gblobal_variables = ssd_filter_variables(tf.global_variables())
            saver = tf.train.Saver(gblobal_variables)

            if mc.LOAD_PRETRAINED_MODEL == False:
                saver.restore(sess, FLAGS.checkpoint)
                print ('restore:',FLAGS.checkpoint)

            with open(FLAGS.eval_file) as f:
                files_list = f.readlines()
            
            all_num = len(files_list)
            img_idx = 0
            
            for f in files_list:
                filename = f.strip() + '.jpg'
                f = FLAGS.images_path + '/' + filename
                
                #print ('f:',f) 
                im = cv2.imread(f)
                #im = im.astype(np.float32, copy=False) 
                src_h, src_w, _ = [float(v) for v in im.shape]
                im = cv2.resize(im, (mc.IMAGE_WIDTH, mc.IMAGE_HEIGHT))

                im = im - mc.BGR_MEANS
                input_image = im

                orig_h, orig_w, _ = [float(v) for v in im.shape]
                #print ('image rows:{} image cols:{}'.format(orig_h,orig_w))

                #conv1_1 = sess.run([model.conv1_1],feed_dict={model.image_input:[input_image]})
                det_boxes, det_probs = sess.run(
                    [model.decode_boxes, model.mbox_conf],
                    feed_dict={model.image_input:[input_image]})

                det_probs[:,:,0] = 0
                probs = det_probs
                det_probs = np.max(probs,2)
                det_class = np.argmax(probs,2)
                
                # Filter
                final_boxes, final_probs, final_class = model.filter_prediction(
                                            det_boxes[0], det_probs[0], det_class[0])

                final_boxes_arr = np.array(final_boxes)
                scale_width = float(src_w) / float(orig_w)
                scale_height = float(src_h) / float(orig_h)
                final_boxes_arr[:,0::2] *=  scale_width
                final_boxes_arr[:,1::2] *=  scale_height
                    
                save_eval_res(mc,filename,src_h,src_w,final_boxes_arr,final_probs,final_class)
                
                keep_idx    = [idx for idx in range(len(final_probs)) \
                                            if final_probs[idx] > mc.PLOT_PROB_THRESH]
                final_boxes = [final_boxes_arr[idx] for idx in keep_idx]
                final_probs = [final_probs[idx] for idx in keep_idx]
                final_class = [final_class[idx] for idx in keep_idx]
      
                
                print ('image name:{} {}/{}'.format(filename,img_idx,all_num))
                img_idx += 1
            
def main(argv=None):
    eval()
    
if __name__ == '__main__':
    tf.app.run()
