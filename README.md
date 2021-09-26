# plebMTG.ai

Developer: Cheng Hao Ke

Quality Assurance: Brian Rice

---

<!-- toc -->

- [Directory structure](#directory-structure)
- [Functions](#Functions)
- [Running the app](#running-the-app)
  * [1. Build the docker image](#1-build-the-docker-image)
  * [2. Data ingestion and storage](#2-data-ingestion-and-storage)
  * [3. Database data insertion](#3-database-data-insertion)
  * [4. Initialize the database](#4-initialize-the-database)
  * [5. Run the entire model pipeline](#5-run-the-entire-model-pipeline)
  * [6. Only run the models](#6-only-run-the-models)
  * [7. Run tests inside docker](#7-run-tests-inside-docker)
  * [8. Run app](#8-run-app)
  * [9. Database operations](#9-database-operations)
  * [10. Kill the container](#10-kill-the-container)
- [Testing](#testing)

<!-- tocstop -->

## Project charter

### Background
Magic: The Gathering ([MTG](https://magic.wizards.com/en/content/history)) was the first trading card game (TCG) and 
one of the largest physical and digital card game played in the world. The game includes tens of thousands of unique 
cards and billions of variations and copies of these cards in [11 languages](https://www.washingtonpost.com/magazine/2020/07/29/after-nearly-30-years-game-magic-gathering-is-bigger-than-ever-best-players-may-also-be-teaching-us-about-heroism/) 
since its inception in 1993. The game has continued to grow, attracting millions of players and making
 [581.2 million USD in 2020 alone](https://www.forbes.com/sites/joeparlock/2021/02/09/magic-the-gathering-had-its-best-financial-year-ever-in-2020/?sh=63e7fa1b1f0a).
MTG is commonly sold in booster packs containing a semi-randomized subset of cards from a single set. This method 
of distribution has allowed a vibrant secondary card market to flourish. Players often opt to buy single cards instead 
of buying the randomized boosters to obtain the right cards for their deck. 
&nbsp;  
&nbsp;  
However, price speculation, insider trading, and a host of other problems meant that the price for individual cards is 
extremely unstable and similar in nature to 
stocks and cryptocurrencies. A quick search on Google would return numerous forum threads and [articles](https://www.hipstersofthecoast.com/2015/10/wwl-regulating-the-market/) 
discussing and complaining about the state of the secondary card market. Standard MTG games and competitions are 
played using decks of 60 cards (with another 15 cards in the sideboard). In general, a single MTG deck may contain up
to 4 copies of the same card. Thus, the average MTG player would often find themselves forced to invest considerable
amounts of money obtaining multiple copies of the same card to build a playable deck. 
Exacerbating this problem is the volatile nature of card prices, which could result in substantial losses to the player. 

### Vision
This app enhances the average player's ability to maximize limited financial resources and increase understanding of 
the factors that lead to card price changes.

### Mission
This app assists the average MTG player's use of limited financial resources by identifying 
suitable card substitutes for deck construction and predicting future card price movements. Players can utilize the app's
state-of-the-art machine learning and statistical models to obtain cards similar to competitive staples for their 60+15 
card decks. The app also uses supervised learning models to predict card price changes, arming players with 
information on when certain purchases should be made to avoid an investment loss. Players would be able to 
obtain a better understanding of what card gameplay characteristics influence its price movements and usage statistics. 
&nbsp;  
&nbsp;  
Specifically, the app focuses on cards that are [standard legal](https://magic.wizards.com/en/content/standard-formats-magic-gathering) 
(cards in the most recent 5-8 sets). It utilizes a combination of unsupervised and supervised models to provide similar 
card recommendations and price change predictions. A large variety of card gameplay [characteristics](https://mtg.fandom.com/wiki/Parts_of_a_card) 
would be used as predictors within the models (e.g. mana cost, power, toughness, type, etc.).  

### Data source
- [Scryfall API](https://scryfall.com/docs/api): provides data on card characteristics and its most recent price
- [MTGJSON API](https://mtgjson.com/): provides data on card characteristics and historical price data
- [MTGGoldfish website](https://www.mtggoldfish.com/): provides card usage statistics in different MTG formats

### Success criteria
1. Model performance metrics:
    - Unsupervised learning: Silhouette score, pseudo-F statistic, and elbow plots would be used to choose and implement 
    the optimal number of clusters.
    - Supervised learning: obtain significant coefficients from card attribute variables (p-value < 0.05) to help players understand the influence of attributes on price.
2. Business metrics:
    - Average daily/monthly users: The number of users who are using the app. Clickstream data would be captured using 
    tracking frameworks.
    - Average money saved from using the app: Results would be obtained using a randomized control trial (RCT) 
    comparing players who used the app and players who don't. Analyses would be conducted on the differences between 
    money spent on individual cards by players.

&nbsp;  
## Directory structure 

```
├── README.md                         <- You are here
├── app
│   ├── static/                       <- Contains all CSS and Javascript files
│   ├── templates/                    <- Contains all HTML files
│   ├── boot.sh                               
│
├── config                            
│   ├── local/                        
│   ├── logging/                     
│   ├── flaskconfig.py                <- Flask app configurations
│   ├── plebmtg.yaml                  <- Default configurations
│
├── data                              
│   ├── external/                    
│   ├── sample/                      
│
├── deliverables/                                           
│
├── figures/                         
│
├── models/                          
│
├── references/                       
│
├── src/                              
│   ├── ingestion/                    <- Contains API ingestion and data cleaning codes
│   ├── storage/                      <- Contains read/write to database and S3 Bucket codes
│   ├── statistics/                   <- Contains all statistics related functions
│   ├── utils/                        <- Additional helper functions
│
├── test/                             
│
├── app.py                            <- Function to run everything on the Flask app
├── run.py                            <- Function to run everything using the command line
├── Dockerfile                        <- Dockerfile to run functions locally
├── Dockerfile_app                    <- Dockerfile to run the Flask app
├── Makefile                          <- Shortcuts to run all functions
├── requirements.txt
```

## Functions
All functions are located inside the `src/` folder.
- The `ingestion/` folder contains all functions used for obtaining data from APIs and preliminary data cleaning
- The `statistics/` folder contain different statistical functions for use when constructing the model
- The `storage/` folder contains all functions used for storing and reading data from S3 buckets and database servers
- The `utils/` folder contains additional helper functions to reduce the need to write repetitive code
- Codes were written to allow for line by line debugging inside IDEs like PyCharm. Hence custom function import try except codes are added to ensure imports will not cause `ModuleNotFoundError`s.

## Running the app
### 1. Build the docker image
Before using the functions / classes provided in this project, build the docker image so that it may run smoothly.
To build the image, navigate to the base of this repository and run in the terminal the following code:
```bash
docker build -t chmsia423 .
```

### 2. Data ingestion and storage
To obtain data from all three APIs and store them inside an S3 bucket using docker with default values, simply run:
```bash
docker run -it \
    -e AWS_ACCESS_KEY_ID=yourid \
    -e AWS_SECRET_ACCESS_KEY=yourkey \
    chmsia423 run.py ingests3
```
The `ingests3` option also custom name options for all three datasource inputs `--item1-3 itemname`.
You can also specify a different bucket name with `--bucket yourbucketname` 

### 3. Database data insertion
To store the data inside S3 into a database of your choice using default settings, run the following code:
```
docker run -it \
    -e MYSQL_HOST=url \
    -e MYSQL_PORT=3306 \
    -e MYSQL_USER=user \
    -e MYSQL_PASSWORD=psw \
    -e MYSQL_DATABASE=msia423_db \
    -e AWS_ACCESS_KEY_ID=keyid \
    -e AWS_SECRET_ACCESS_KEY=key \
    chmsia423 run.py s3rds
```
You can also use the following command to obtain the same results:
```
docker run -it \
    -e AWS_ACCESS_KEY_ID=keyid \
    -e AWS_SECRET_ACCESS_KEY=key \
    chmsia423 run.py s3rds --user user --password psw
```
The `create_db` option also includes the option `replace` which allows the user to either overwrite or append to an existing table.
  
Note you can also use the `Refresh data` option inside the Flask app to refresh the data (locally only)

### 4. Initialize the database 
To create an empty SQL table, run the following code:
```bash
docker run -it \
    -e MYSQL_HOST=url \
    -e MYSQL_PORT=3306 \
    -e MYSQL_USER=user \
    -e MYSQL_PASSWORD=psw \
    -e MYSQL_DATABASE=msia423_db \
    chmsia423 run.py sqlempty
```

### 5. Run the entire model pipeline
Read data from S3, run models and insert the results into RDS
```bash
make docksql
```

### 6. Only run the models
Read data from S3 and run models only
```bash
make dockergoogle
```

### 7. Run tests inside docker
Run tests inside docker
```bash
docker run -it chmsia423 -m pytest test/
```

### 8. Run app
Run the Flask app inside docker
```bash
make imageapp
make dockerflask
```

### 9. Database operations
To create new users inside the database, run:
```SQL
CREATE USER 'msia423instructor'@'%' IDENTIFIED BY 'password';
```
To query data directly from the database, run:
```SQL
SELECT * FROM msia423_db.cluster_result
```

### 10. Kill the container 

Once finished with the app, you will need to kill the container. To do so: 

```bash
docker kill chmsia423 
```

where `chmsia423` is the name of the docker image given in the `docker run` command.

 
