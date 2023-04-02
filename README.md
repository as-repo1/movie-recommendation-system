# movie-recommendation-system

## **About**

This code is used to process movie data from two different CSV files and merge them into one using the title of the movies. It then selects specific features and processes them to prepare for the vectorization of text. The goal of this is to create a content-based recommendation system for movies.

## **Requirements**

- numpy
- pandas

## **How to Use**

1. Download the **`tmdb_5000_movies.csv`** and **`tmdb_5000_credits.csv`** files
2. Place the files in the same directory as the **`recommendation_system.py`** file
3. Run the code
4. The code will output a DataFrame with movie titles and their corresponding tags, which will be used for content-based recommendation.

## **Process**

1. Import the necessary libraries: numpy and pandas
2. Import the CSV files into two separate DataFrames
3. Merge the two DataFrames into one using the "title" column
4. Select specific features needed for the recommendation system
5. Convert the string values in certain columns into lists using the ast library
6. Convert the lists into strings with spaces between each value
7. Concatenate the selected columns into one column
8. Vectorize the text for use in a content-based recommendation system
