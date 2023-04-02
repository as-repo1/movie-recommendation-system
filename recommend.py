#!/usr/bin/env python

import numpy as np
import pandas as pd
mv = pd.read_csv("tmdb_5000_movies.csv")
cr = pd.read_csv("tmdb_5000_credits.csv")

movies = mv.merge(cr,on="title")

movies = movies[["movie_id","title","overview","genres","keywords","cast","crew"]]

movies.dropna(inplace = True)
import ast

def convert(obj):
    l =[]
    for i in ast.literal_eval(obj):
        l.append(i["name"])
    return l

movies["genres"] = movies["genres"].apply(convert)
movies["keywords"] = movies["keywords"].apply(convert)

def convert_3(obj):
    l = []
    cou = 0
    for i in ast.literal_eval(obj):
        if cou != 3:
            l.append(i["name"])
            cou += 1
        else:
            break
    return str(l)

def fetch_director(obj):
    l =[]
    for i in ast.literal_eval(obj):
        if i["job"] == "Director":
            l.append(i["name"])
    return l
movies["overview"] = movies["overview"].apply(lambda x:x.split())
movies["genres"] = movies["genres"].apply(lambda x:[i.replace(" ","") for i in x])
movies["keywords"] = movies["keywords"].apply(lambda x:[i.replace(" ","") for i in x])
movies["crew"] = movies["crew"].apply(lambda x:[i.replace(" ","") for i in x])

for index, row in movies.iterrows():
    new_cast = []
    for actor in row["cast"]:
        new_cast.append(actor.replace(" ", ""))
    movies.at[index, "cast"] = new_cast

movies["tags"] = movies["overview"] +  movies["genres"] + movies["keywords"] +  movies["cast"] +  movies["crew"]

movie = movies[["movie_id","title","tags"]]

movie["tags"].apply(lambda x:" ".join(x))

movie["tags"] = movie["tags"].apply(lambda x:" ".join(x)) #with warning

from sklearn.feature_extraction.text import CountVectorizer
cv = CountVectorizer(max_features=5000,stop_words="english")

vectors = cv.fit_transform(movie["tags"]).toarray()
import nltk
from nltk.stem.porter import PorterStemmer

ps = PorterStemmer()

def stem(text):
    y = []
    for i in text.split():
        y.append(ps.stem(i))
    return " ".join(y)

movie["tags"] = movie["tags"].apply(stem)

vectors[0]

from sklearn.metrics.pairwise import cosine_similarity

similarity = cosine_similarity(vectors)

sorted(list(enumerate(similarity[0])),reverse = True,key=lambda x:x[1])[1:6]

def recommend(movies):
    movie_index = movie[movie["title"] == movie].index[0]
    distances = similarity[movie_index]
    movie_list = sorted(list(enumerate(distances)),reverse=True,key=lambda x:x[1])[1:6]
    
    for i in movie_list:
        #print(i[0])
        print(movie.iloc[i[0]].title)

user_input = input("Enter the Movie name: ")
recommend ("user_input")
