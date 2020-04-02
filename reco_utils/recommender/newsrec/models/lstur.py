import numpy as np
import tensorflow as tf
import tensorflow.keras as keras
from tensorflow.keras import layers


from reco_utils.recommender.newsrec.models.base_model import BaseModel
from reco_utils.recommender.newsrec.models.layers import AttLayer2, ComputeMasking, OverwriteMasking

__all__ = ["LSTURModel"]

class LSTURModel(BaseModel):
    '''LSTUR model(Neural News Recommendation with Multi-Head Self-Attention)

    Mingxiao An, Fangzhao Wu, Chuhan Wu, Kun Zhang, Zheng Liu and Xing Xie: 
    Neural News Recommendation with Long- and Short-term User Representations, ACL 2019

    Attributes:
        word2vec_embedding (numpy.array): Pretrained word embedding matrix.
        hparam (obj): Global hyper-parameters.
    '''
    def __init__(self, hparams, iterator_creator_train, iterator_creator_test):
        """Initialization steps for LSTUR.
        Compared with the BaseModel, LSTUR need word embedding.
        After creating word embedding matrix, BaseModel's __init__ method will be called.
        
        Args:
            hparams (obj): Global hyper-parameters. Some key setttings such as type and gru_unit are there.
            iterator_creator_train(obj): LSTUR data loader class for train data.
            iterator_creator_test(obj): LSTUR data loader class for test and validation data
        """
        
        self.word2vec_embedding = self._init_embedding(hparams.wordEmb_file)
        self.hparam = hparams
        
        super().__init__(hparams, iterator_creator_train, iterator_creator_test)

    def _init_embedding(self, file_path):
        """Load pre-trained embeddings as a constant tensor.
        
        Args:
            file_path (str): the pre-trained embeddings filename.

        Returns:
            np.array: A constant numpy array.
        """
        return np.load(file_path).astype(np.float32)


    def _build_graph(self):
        """Build LSTUR model and scorer.

        Returns:
            obj: a model used to train.
            obj: a model used to evaluate and inference.
        """

        model, scorer = self._build_lstur()
        return model, scorer

    def _build_userencoder(self, titleencoder, type='ini'):
        '''The main function to create user encoder of LSTUR.

        Args:
            titleencoder(obj): the news encoder of LSTUR. 

        Return:
            obj: the user encoder of LSTUR.
        '''
        hparams = self.hparams
        his_input_title = keras.Input(shape=(hparams.his_size, hparams.doc_size),dtype='int32')
        user_indexes = keras.Input(shape=(1,), dtype='int32')

        user_embedding_layer = layers.Embedding(hparams.user_num,
                                 hparams.gru_unit,
                                 trainable=True,
                                 embeddings_initializer='zeros')
        
        long_u_emb = layers.Reshape((hparams.gru_unit,))(user_embedding_layer(user_indexes))
        click_title_presents = layers.TimeDistributed(titleencoder)(his_input_title)

        if type=='ini':
            user_present = layers.GRU(hparams.gru_unit,)(
                layers.Masking(mask_value=0.0)(click_title_presents),
                initial_state=[long_u_emb]
                )
        elif type=='con':
            short_uemb = layers.GRU(hparams.gru_unit,)(layers.Masking(mask_value=0.0)(click_title_presents))
            user_present = layers.Concatenate()([short_uemb, long_u_emb])
            user_present = layers.Dense(hparams.gru_unit)(user_present)

        click_title_presents = layers.TimeDistributed(titleencoder)(his_input_title)
        user_present = AttLayer2(hparams.attention_hidden_dim)(click_title_presents)
        
        model = keras.Model([his_input_title, user_indexes], user_present, name='user_encoder')
        return model
    
    def _build_newsencoder(self, embedding_layer):
        '''The main function to create news encoder of LSTUR.

        Args:
            embedding_layer(obj): a word embedding layer.
        
        Return:
            obj: the news encoder of LSTUR.
        '''
        hparams = self.hparams
        sequences_input_title = keras.Input(shape=(hparams.doc_size,),dtype='int32')   
        embedded_sequences_title = embedding_layer(sequences_input_title)
        
        y = layers.Dropout(hparams.dropout)(embedded_sequences_title)
        y = layers.Conv1D(hparams.filter_num, hparams.window_size, activation=hparams.cnn_activation, padding='same')(y)
        y = layers.Dropout(hparams.dropout)(y)
        y = layers.Masking()(OverwriteMasking()([y, ComputeMasking()(sequences_input_title)])) 
        pred_title = AttLayer2(hparams.attention_hidden_dim)(y)
        
        model =  keras.Model(sequences_input_title, pred_title, name="news_encoder")
        return model
 
    def _build_lstur(self):
        """The main function to create LSTUR's logic. The core of LSTUR
        is a user encoder and a news encoder.
        
        Returns:
            obj: a model used to train.
            obj: a model used to evaluate and inference.
        """
        hparams = self.hparams

        his_input_title = keras.Input(shape=(hparams.his_size, hparams.doc_size),dtype='int32')
        pred_input_title= keras.Input(shape=(hparams.npratio+1, hparams.doc_size),dtype='int32')
        pred_input_title_one = keras.Input(shape=(hparams.doc_size,), dtype='int32')
        imp_indexes = keras.Input(shape=(1,), dtype='int32')
        user_indexes = keras.Input(shape=(1,), dtype='int32')

        embedding_layer = layers.Embedding(
                                    hparams.word_size,
                                    hparams.word_emb_dim,
                                    weights=[self.word2vec_embedding],
                                    trainable=True)

        titleencoder = self._build_newsencoder(embedding_layer) 
        userencoder = self._build_userencoder(titleencoder, type=hparams.type)
        newsencoder = titleencoder

        user_present = userencoder([his_input_title, user_indexes])
        news_present = layers.TimeDistributed(newsencoder)(pred_input_title)
        news_present_one = newsencoder(pred_input_title_one)

        preds = layers.Dot(axes=-1)([news_present, user_present])
        preds = layers.Activation(activation='softmax')(preds)

        pred_one = layers.Dot(axes=-1)([news_present_one, user_present])
        pred_one = layers.Activation(activation='sigmoid')(pred_one)

        model = keras.Model([imp_indexes, user_indexes, his_input_title, pred_input_title], preds)
        scorer = keras.Model([imp_indexes, user_indexes, his_input_title, pred_input_title_one], pred_one)

        return model, scorer

