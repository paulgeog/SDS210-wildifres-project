
# Mapping Wildfires
### *by Paul Ghisletti, as part of the SDS210 course spring '26*
This project aims at pulling wildfire data from an API provided by Fire Information for Resource Management System (FIRMS), which is a  by NASA, and visualising this data through an automated pipeline to gain insights into the distribution, severity and other factors concerning wild fires, both globally and locally.  

It is presented in two notebooks: `visualise_wildfires.ipynb` for easy-to-use API access and visualisation, and `wildfires.ipynb` for an in-depth review of the inner workings. All code in `/src` mirrors `wildfires.ipynb`, with the addition of `/src/inputs.py` which handles user input for `visualise_wildfires.ipynb`.
## 1. Repository structure
```
├── data
│   └── raw
│       ├── 198_countries.gpkg          # normalised country boundaries
│       ├── 7_continents.gpkg           # normalised continent boundaries
│       ├── continent_boundaries_7.gpkg # raw continent boundaries
│       └── ne_10m_admin_0_countries/   # raw country boundaries
├── environment.yml
├── notebooks
│   ├── countries_normalisation.ipynb
│   ├── visualise_wildfires.ipynb       # user friendly API access
│   └── wildfires.ipynb                 # detailed project report
├── README.md
└── src                                 # contains code for visualise_wildfires.ipynb
```
## 2. Getting started
### 2.1. Requirements
- Conda (Miniconda or Anaconda)
- Python 3.12
- dependencies listed in `environment.yml`
- `nbstripout` for automatic notebook cleanup (installed via environment but requires additional step). This is only needed when committing `.ipynb` files to the repository. Not for users who just run the project.

#### 2.1.1. Installation of dependencies
Create and activate the new conda environment:
```bash
conda env create -f environment.yml
conda activate sds210-project-wildfires-env
```
#### 2.1.2. Enable notebook output stripping
Inside the activated environment:
```bash
nbstripout --install
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
**Make sure the `.env` file is in the main directory of the repository.**
### 2.3. Run
Then, open the `wildfires.ipynb` or `visualise_wildfires.ipynb` jupyter notebook and execute the cells.
## 3. Resources
### 3.1. FIRMS API
This is an API provided by NASA in scope of the FIRMS program. More information can be found here: https://firms.modaps.eosdis.nasa.gov/api/  

For more attribute information:
https://www.earthdata.nasa.gov/data/tools/firms/active-fire-data-attributes-modis-viirs 
### 3.2. World geometries
**Geopackage for country boundaries:**  
https://www.geoboundaries.org/globalDownloads.html   

**Geopackage for continent boundaries:**  
https://www.kaggle.com/datasets/ericnarro/continent-boundaries-as-gpkg-files?resource=download  
This download contains a `.gpkg` for both a 7-continent and an 8-continent definition.