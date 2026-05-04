
# Mapping Wildfires
### *by Paul Ghisletti, as part of the SDS210 course spring '26*
This project aims at pulling wildfire data from an API provided by Fire Information for Resource Management System (FIRMS), which is a programm by NASA, and visualising this data to gain insigts and answer some predefined questions.
## 1. Description
An in-depth description of the projects structure, purpose and inner workings
## 2. Getting started
### 2.1. Requirements
- Python 3.10+
- pip packages listed in requirements.txt  

Install dependencies inside your environment:
```bash
pip install -r requirements.txt
```
### 2.2. API Key
#### 2.2.1. Get individual API-key
You need to request your individual API key from FIRMS:
https://firms.modaps.eosdis.nasa.gov/api/map_key  

The FIRMS MAP_KEY is rate-limited (requests are restricted within a short time window). If you exceed the limit, you must wait before making additional requests.
#### 2.2.2. Setting your API-key in this repository
Create a new `.env` file:  
```env
MY_API_KEY=your_api_key_here
``` 
or you can copy the existing template:   
```bash
cp .env.example .env
```
**Make sure the `.env` file is in the same directory where you run the notebook.**
### 2.3. Run
Then, open the `wildfires.ipynb` jupyter notebook and execute the cells.
## 3. Ressources
### 3.1. FIRMS API
This is an API provided by NASA in scope of the FIRMS program. More information can be found here: https://firms.modaps.eosdis.nasa.gov/api/ 