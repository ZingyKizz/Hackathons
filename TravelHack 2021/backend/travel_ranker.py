import pandas as pd
import six
import requests
from sqlalchemy import create_engine
from abc import ABC, abstractmethod
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
import json
import nltk
import pymorphy2
from nltk.corpus import stopwords
from string import punctuation
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re

class SQLSession(ABC):
    def __init__(self, *, server, port, db, user, password, silent=False):
        """
        Parameters
        ----------
        :type server: str
        :type port: str
        :type db: str
        :type user: str
        :type password : str
        :type silent: bool
        Returns
        -------
        Session object
        """
        if not (
                isinstance(server, six.string_types)
                and isinstance(db, six.string_types)
        ):
            raise TypeError('server and db arguments should be strings')
        if not (
                isinstance(user, six.string_types)
                and isinstance(password, six.string_types)
        ):
            raise TypeError('user and password arguments should be strings')

        self.server = server
        self.port = port
        self.db = db
        self.user = user
        self.password = password

        self.engine = self.make_engine()
        self.con = self.engine.connect()
        self.is_connected = True
        if not silent:
            self.print_message()
        self.is_silent = silent

    def print_message(self, symbol='-'):
        fill_length = max(len(f'Server: {self.server}'), len(f'Database: {self.db}'), len(f'User: {self.user}'))
        fill = f'{fill_length * symbol}'
        message = f'Connected to\n{fill}\nServer: {self.server}\nDatabase: {self.db}\nUser: {self.user}\n{fill}'
        print(message)

    @abstractmethod
    def make_engine(self):
        raise NotImplementedError

    @abstractmethod
    def select_statement(self, query):
        """Returns result of select-query as DataFrame
        Parameters
        ----------
        :type query: str
        Returns
        -------
        pd.DataFrame
        """
        raise NotImplementedError

    @abstractmethod
    def exec_sp(self, sp_name, params):
        """
        Executes stored procedure with specified list of params
        Parameters
        ----------
        :type sp_name: str
        :type params: list
        Returns
        -------
        None
        """
        raise NotImplementedError

    def df_to_db(self, df, table_fullname, index=False, if_exists='fail', **kwargs):
        """Writes DataFrame to database
        Parameters
        ----------
        :type df: pd.DataFrame
        :type table_fullname: str
        :type index: bool
        :type if_exists: str
        :param kwargs: additional parameters for pd.to_sql() method
        Returns
        -------
        None
        """
        if not isinstance(table_fullname, six.string_types):
            raise TypeError('table_fullname argument should be a string')
        try:
            schema_name, table_name = table_fullname.split('.')
        except ValueError as e:
            raise Exception('table_fullname argument should be like "schema_name.table_name"') from e
        df.to_sql(name=table_name, index=index, schema=schema_name, con=self.con,
                  if_exists=if_exists, **kwargs)

    def close(self):
        """Closes connection"""
        if self.is_connected:
            self.con.close()
            self.is_connected = False
            message_ = 'Connection closed'
        else:
            message_ = 'Connection is already closed'
        if not self.is_silent:
            fill_symbol = '-'
            fill_length = len(message_)
            message = f'{fill_symbol * fill_length}\n{message_}\n{fill_symbol * fill_length}'
            print(message)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

        
class PostgreSQLSession(SQLSession):
    """Provide connection to PostgreSQL databases"""
    def make_engine(self):
        engine = create_engine(f'postgresql://{self.user}:{self.password}@{self.server}:{self.port}/{self.db}')
        return engine

    def select_statement(self, query):
        if not isinstance(query, six.string_types):
            raise TypeError('query argument should be a string')
        return pd.read_sql(query, con=self.con)

    def exec_sp(self, sp_name, params):
        raise NotImplementedError



class Ranker:
    ETALON_JSON = "etalon.json"
    PLACES_TABLE = "places"
    RATINGS_TABLE = "ratings"    

    SERVER = "213.232.229.188"
    PORT = "5432"
    DB = "tourism_demo_db"
    USER = "root"
    PASSWORD = "root"

    INFO_COLS = ["id", "title", "description", "image_link"]

    DEFAULT_IMAGE = 'https://i.pinimg.com/originals/8a/eb/d8/8aebd875fbddd22bf3971c3a7159bdc7.png'
    
    def __init__(self):
        self.morph = pymorphy2.MorphAnalyzer()
        self.russian_stopwords = stopwords.words("russian")
        
        with PostgreSQLSession(
            server=self.SERVER, 
            port=self.PORT, 
            db=self.DB, 
            password=self.PASSWORD, 
            user=self.USER,
            silent=True
        ) as pg:
            self.our_places_ = pg.select_statement(f"select * from {self.PLACES_TABLE}") 
            self.our_places_ = self.our_places_.merge(self.load_images(), left_on="id", right_on="place_id", how="left", suffixes=("", "_y"))
            self.ratings = pg.select_statement(f"select * from {self.RATINGS_TABLE}").groupby("rateable_id")["value"].mean().reset_index()
            self.our_places_ = (
                self.our_places_
                .merge(self.load_images(), left_on="id", right_on="place_id", how="left", suffixes=("", "_y"))
                .merge(self.ratings, left_on="id", right_on="rateable_id", how="left", suffixes=("", "_y"))
            )
            self.our_places_["image_link"] = self.our_places_["image_link"].fillna(self.DEFAULT_IMAGE)
            self.our_places_pop = 1e-20 * np.log(self.our_places_["value"].fillna(3).to_numpy())
            self.idx_id = {id_: i for i, id_ in enumerate(self.our_places_["id"])}
            self.our_places = [t + " " + d for t, d in zip(self.our_places_["title"], self.our_places_["description"])]
            self.our_places = self.preprocess_text_list(self.our_places)
            
        with open(self.ETALON_JSON, mode="r", encoding="utf-8") as f:
            etalon_places = [p["title"] + " " + p["description"] for p in json.load(f)["places"]]
        self.etalon_places = self.preprocess_text_list(etalon_places)
        
        self.bow = TfidfVectorizer()
        self.fit()
        self.is_fitted = True
        
    def preprocess_text(self, text):
        text = re.sub(r"[^\w]", " ", text)
        words = text.split()
        res = []
        for word in words:
            if word.isdigit():
                continue
            p = self.morph.parse(word)[0]
            res.append(p.normal_form)
        text = " ".join(res)
        return text
    
    def fit(self, top=5):
        self.bow.fit(self.etalon_places)
        
        etalon_places_embed = self.bow.transform(self.etalon_places)
        our_places_embed = self.bow.transform(self.our_places)
        
        self.cs_etalon = cosine_similarity(our_places_embed, etalon_places_embed)
        self.scores = np.mean((-np.sort(-self.cs_etalon, axis=1))[:,:top], axis=1) + self.our_places_pop 
        
        tfidf = TfidfVectorizer()
        our_places_embed_self = tfidf.fit_transform(self.our_places, self.our_places)
        self.cs_our = cosine_similarity(our_places_embed_self, our_places_embed_self)
        
        self.is_fitted = True
        
        
    def _is_fitted_check(self):
        if not self.is_fitted:
            raise NotFittedError
    
    def preprocess_text_list(self, places):
        return [self.preprocess_text(p) for p in places]
    
    def get_json_from_scores(self, scores):
        ranking = np.argsort(scores)[::-1]
        res = self.our_places_.iloc[ranking].loc[:, self.INFO_COLS].to_json(orient="records", force_ascii=False)
        return res
    
    def rank(self):
        self._is_fitted_check()
        return self.get_json_from_scores(self.scores)

    def get_info_by_id(self, id_):
        res = self.our_places_.loc[self.our_places_["id"] == id_, self.INFO_COLS].to_json(orient="records", force_ascii=False)
        return res
        
    def rank_with_history(self, history=None, weight=0.4):
        self._is_fitted_check()
        
        if history is None:
            history = []
        else:
            history = [self.idx_id[p] for p in history]
        
        scores = self.scores.copy()
        
        for coef, place in enumerate(history[::-1], 1):
            coef = (1 / coef) ** 0.15
            bias = self.cs_our[place].copy()
            bias[place] = 0
            scores += coef * weight * bias
            
        return self.get_json_from_scores(scores)
    
    
    def load_images(self):
        data = requests.get("https://murmansk.travel/api/places?&sort=avg&show=id,entity,title,type_id,images,tags,rating,favorited,address,work_hours,type,label,audios&resolution=medium&page=1&count=10000&lang=ru").json()
        ids = []
        images = []
        for place in data["data"]:
            ids.append(place["id"])
            if place["images"]:
                images.append(place["images"][0])
            else:
                images.append(self.DEFAULT_IMAGE)
        res = dict(zip(ids, images))
        res = pd.Series(res).reset_index()
        res.columns = ["place_id", "image_link"]
        return res
