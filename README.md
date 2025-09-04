# CopperCoreAI
March 3, 2025 - June 13, 2025

# PROJECT OVERVIEW:
This project is an advanced Python-based application for detecting potential porphyry copper deposits using magnetic and gravity data. The system processes geophysical daatasets to extract key features, applies machine learning models for predicting and identifying anomalies associated with porphyry copper system. Copper Core AI is designed to improve the efficiency and accuracy of mineral exploration.

# Demo Video:

# Notion Page: [https://www.notion.so/orefox/Demo-Video-for-the-Project-20e05cef1f228037af06f01d51afc049?source=copy_link]


# SET UP INSTRUCTIONS:
## Git Clone Project to download project to Local machine. 
## List of additional packages:
- fiona
- geopandas
- celery
- rasterio
- python-decouple
- h5py
- keras
- numpy
- pandas
- tensorboard
- tensorboard-data-server
- tensorflow
- tensorflow-estimator
- tensorflow-intel

# HOW TO RUN THE WEBSITE AFTER DOWNLOADING

## 0. Connect the database:

- Connect the database.

### * How to connect the database:
- Install PostGIS Database
- [Install the latest version of PostgreSQL][PostgreSQL]
- Go with the default settings for everything except for things mentioned below.
- Check “ADD TO PYTHON PATH” or something similar on one of the pages.
- You might be asked to create a password during installation, make the password as `pass`(or change the passwords in the later steps).
- When on this page, select PostGIS in spatial extensions:

![gisExtension](https://i.imgur.com/wnGnOgX.jpg)


- After the page above, you might encounter a checkbox to create a spatial database, no need to check that.
- SQL Shell and pgAdmin4 will be installed automatically once the installation above finishes.

### pgAdmin4
- Open `pgAdmin4` and log in with the password used during installation.
- Go to `Servers -> PostgreSQL 17 -> Databases` and right-click it to create a new database named `CopperAI`.
- Go to `Servers -> PostgreSQL 17 -> Databases -> CopperAI -> extensions`
- Right-click on extensions and select `create -> extension`
- Search and select `postgis` extension from the options(option not available in the image as already added)

### SQL Shell
- Open `SQL Shell`. Everything in square brackets is the default value. Hit enter to keep the default values. Only change the default value of Database to `CopperAI` and Password to `pass` (installation password).

  ![image](https://github.com/user-attachments/assets/77c44d0d-1a2b-4201-b49b-c58037d350f7)


## 1. Create and activate a virtual environment:
  ```shell
  py -3.9 -m venv venv39
  .\venv39\Scripts\activate.ps1
```
## 2. Install all the required packages:
```shell
  py -m pip install --upgrade pip setuptools wheel
  pip install GDAL-3.3.3-cp39-cp39-win_amd64.whl
  python -m pip install -r requirements.txt
```
- Check if the requirements were installed using `pip list`
## 3. Set up to connect the database.
- Make these changes in .env (installation password is used here)
  
![image](https://github.com/user-attachments/assets/4c392298-2a05-4856-84a2-bc8216d48732)

<!-- - Then go to your virtual environment folder (venv) outside the web folder and move to `venv -> Lib -> djconfig -> admin.py` and edit line 29.
  	Change
                  `from django.conf.urls import url`
        to
                  `from django.urls import re_path as url` -->
## 4. Run the website:
- Make sure the directory is changed to `web` before executing the following (command prompt for Windows users):
```
python manage.py makemigrations
python manage.py migrate
```
- Within the same terminal, execute: `python manage.py runserver`
- Visit this link http://127.0.0.1:8000/
  
![image](https://github.com/user-attachments/assets/27b2689c-1ae0-4910-93af-bd23ffdc23a4)

## 5. Run the Redis Server:

This guide walks you through installing **Redis (via Memurai)** and **Celery** on a Windows system using **Python 3.9**.

---

### 4.1. Install Redis

#### Download and Install Memurai (Windows-compatible Redis)

- Visit the official **[Memurai website](https://www.memurai.com/)**.
- Download the installer for Windows.
- Run the installer and follow the on-screen prompts to complete the installation.

#### Start Redis

To start Redis using PowerShell, run:

```powershell
memurai
```

#### Verify Redis:

- Confirm Redis is running on the default port (6379):
  
```
redis-cli ping
```
![image](https://github.com/user-attachments/assets/5f6ce4c9-9b13-4a43-b30b-8de27198bfb4)

### 4.2. Install Celery

- Already installed in part 2. 

- Make sure Configure Celery in **settings.py** of **coppercoreai** folder:

![image](https://github.com/user-attachments/assets/75fb4a15-02fd-46c2-91df-c8fa9834b05c)


### 4.3. Run Celery:

- In the new terminal, activate a Virtual Environment
- And run the command:
```
- celery -A coppercoreai worker --loglevel=debug --pool=solo
```

![image](https://github.com/user-attachments/assets/94e62326-3fdc-4ec3-b648-2ab819bfa227)

# IMPORTANT NOTES:
- 1. Link for datasets used for training model: The training area will be all of Queensland
data here https://geoscience.data.qld.gov.au/dataset/ds000018

Search and test data will be from an area in southwest Queensland called the “Texas Orocline”
https://geoscience.data.qld.gov.au/data/magnetic/mg001089

- 2. Incomplete Tasks:

This project doesn't support: 
**LLM integration**, 
**Real-Time Processing** - Capability to process streaming geophysical data for real-time predictions,
**Cloud-Based Functionality** - Deploy the application on a cloud platform for scalability and collaboration. - Remote execution and results sharing via web dashboards.
**Mobile Application** - Companion app for field geologists to view predictions and integrate field observations. **Collaboration Tools** - Shared dashboards for teams to work on the same project. - Real-time commenting on predictions and models.  

- 3. Important Information:
Our team has used CNN as a predictive model for identifying copper porphyry. However, in the provided repository a code file has been uploaded for RANDOM FOREST MODEL and it is correct but not trained due to lacking appropraite data. Theerefore, next team can use the code to train RF model on their datasets. 










