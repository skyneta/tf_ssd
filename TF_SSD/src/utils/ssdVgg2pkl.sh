python caffemodel2pkl.py \
--prototxt_path=./caffe_model/VGG_ILSVRC_16_layers_fc_reduced_deploy.prototxt \
--caffemodel_path=./caffe_model/VGG_ILSVRC_16_layers_fc_reduced.caffemodel \
--caffe_weights_path=./SSD_VGG_16.pkl


mv SSD_VGG_16.pkl ../../data/pretrain
