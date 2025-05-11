# app.py - Application multi-datasets avec interface moderne
import os
import json
import logging
import datetime
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for

import ee

app = Flask(__name__)

# Configuration
SERVICE_ACCOUNT_KEY_FILE = 'terrasight-459208-fe0b0ae226b9.json'  # Chemin vers votre fichier de clé

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Vérifier l'existence du fichier de clé
if not os.path.exists(SERVICE_ACCOUNT_KEY_FILE):
    logger.error(f"ERREUR: Fichier de clé non trouvé: {SERVICE_ACCOUNT_KEY_FILE}")
    logger.error("Veuillez placer votre fichier de clé de compte de service dans le répertoire courant.")

def initialize_earth_engine():
    """Initialise Earth Engine avec le compte de service."""
    try:
        credentials = ee.ServiceAccountCredentials(None, SERVICE_ACCOUNT_KEY_FILE)
        ee.Initialize(credentials)
        logger.info("Earth Engine initialisé avec succès!")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de Earth Engine: {str(e)}")
        return False

# Initialiser Earth Engine au démarrage de l'application
if not initialize_earth_engine():
    logger.error("Impossible d'initialiser Earth Engine. L'application risque de ne pas fonctionner correctement.")

# Définition des datasets disponibles regroupés par catégorie
DATASETS = {
    "climate": [
        {
            "id": "NASA/ORNL/DAYMET_V4",
            "name": "DAYMET V4 - Données Climatiques Quotidiennes",
            "description": "Données météorologiques quotidiennes à résolution 1km pour l'Amérique du Nord.",
            "variables": [
                {"id": "tmax", "name": "Température maximale (°C)", "type": "continuous"},
                {"id": "tmin", "name": "Température minimale (°C)", "type": "continuous"},
                {"id": "prcp", "name": "Précipitations (mm/jour)", "type": "continuous"},
                {"id": "srad", "name": "Rayonnement solaire (W/m²)", "type": "continuous"},
                {"id": "vp", "name": "Pression de vapeur (Pa)", "type": "continuous"},
                {"id": "swe", "name": "Équivalent en eau de neige (kg/m²)", "type": "continuous"},
                {"id": "dayl", "name": "Durée du jour (s)", "type": "continuous"}
            ],
            "default_date": "2020-07-15",
            "date_range": ["1980-01-01", "2021-12-31"],
            "default_region": [-140, 15, -60, 60],  # [ouest, sud, est, nord]
            "default_zoom": 3,
            "default_center": [-100, 40]  # [longitude, latitude]
        },
        {
            "id": "NOAA/GFS0P25",
            "name": "NOAA GFS - Prévisions Météorologiques Globales",
            "description": "Système de prévision global (GFS) de la NOAA avec résolution 0.25 degrés.",
            "variables": [
                {"id": "temperature_2m_above_ground", "name": "Température à 2m (K)", "type": "continuous"},
                {"id": "u_component_of_wind_10m_above_ground", "name": "Vent - composante U à 10m (m/s)", "type": "continuous"},
                {"id": "v_component_of_wind_10m_above_ground", "name": "Vent - composante V à 10m (m/s)", "type": "continuous"},
                {"id": "relative_humidity_2m_above_ground", "name": "Humidité relative à 2m (%)", "type": "continuous"},
                {"id": "total_precipitation_surface", "name": "Précipitations totales (kg/m²)", "type": "continuous"}
            ],
            "default_date": datetime.datetime.now().strftime('%Y-%m-%d'),
            "date_range": ["2015-01-01", datetime.datetime.now().strftime('%Y-%m-%d')],
            "default_region": [-180, -90, 180, 90],  # Monde entier
            "default_zoom": 2,
            "default_center": [0, 0]
        }
    ],
    "weather": [
        {
            "id": "UCSB-CHG/CHIRPS/DAILY",
            "name": "CHIRPS - Précipitations Quotidiennes",
            "description": "Ensemble de données de précipitations infrarouge à haute résolution.",
            "variables": [
                {"id": "precipitation", "name": "Précipitations (mm/jour)", "type": "continuous"}
            ],
            "default_date": "2020-01-15",
            "date_range": ["1981-01-01", datetime.datetime.now().strftime('%Y-%m-%d')],
            "default_region": [-30, -35, 60, 35],  # Afrique et Europe
            "default_zoom": 2,
            "default_center": [17.93, 7.71]
        },
        {
            "id": "NOAA/GOES/16/MCMIPC",
            "name": "NOAA GOES-16 - Imagerie Satellite",
            "description": "Données d'imagerie du satellite GOES-16 (Hémisphère Occidental).",
            "variables": [
                {"id": "CMI_C01", "name": "Canal Bleu", "type": "continuous"},
                {"id": "CMI_C02", "name": "Canal Rouge", "type": "continuous"},
                {"id": "CMI_C03", "name": "Canal Végétation", "type": "continuous"},
                {"id": "CMI_C13", "name": "Canal Infrarouge", "type": "continuous"}
            ],
            "default_date": "2022-01-01",
            "date_range": ["2017-01-01", datetime.datetime.now().strftime('%Y-%m-%d')],
            "default_region": [-100, 10, -50, 45],  # Amérique du Nord et Caraïbes
            "default_zoom": 3,
            "default_center": [-75, 37]
        }
    ],
    "terrain": [
        {
            "id": "USGS/SRTMGL1_003",
            "name": "SRTM - Modèle Numérique de Terrain 30m",
            "description": "Modèle d'élévation global à haute résolution (30m) de la mission SRTM.",
            "variables": [
                {"id": "elevation", "name": "Élévation (m)", "type": "continuous"}
            ],
            "default_date": None,  # Données statiques (pas de date)
            "date_range": None,
            "default_region": [-120, 25, -70, 50],  # Amérique du Nord
            "default_zoom": 4,
            "default_center": [-95, 38]
        },
        {
            "id": "USGS/GTOPO30",
            "name": "GTOPO30 - Modèle Numérique de Terrain Global",
            "description": "Modèle d'élévation global (résolution ~1km).",
            "variables": [
                {"id": "elevation", "name": "Élévation (m)", "type": "continuous"}
            ],
            "default_date": None,  # Données statiques (pas de date)
            "date_range": None,
            "default_region": [-180, -60, 180, 85],  # Monde entier
            "default_zoom": 2,
            "default_center": [0, 20]
        }
    ]
}

def get_dataset_info(dataset_id):
    """Récupère les informations sur un dataset à partir de son ID."""
    for category in DATASETS:
        for dataset in DATASETS[category]:
            if dataset["id"] == dataset_id:
                return dataset
    return None

def get_vis_params(dataset_id, variable):
    """Renvoie des paramètres de visualisation adaptés pour un dataset et une variable."""
    
    # DAYMET V4
    if dataset_id == "NASA/ORNL/DAYMET_V4":
        if variable == "tmax" or variable == "tmin":
            return {
                "min": -40.0,
                "max": 30.0,
                "palette": ['1621A2', 'white', 'cyan', 'green', 'yellow', 'orange', 'red']
            }
        elif variable == "prcp":
            return {
                "min": 0.0,
                "max": 50.0,
                "palette": ['white', 'blue', 'purple', 'cyan', 'green', 'yellow', 'orange', 'red']
            }
        elif variable == "srad":
            return {
                "min": 0.0,
                "max": 400.0,
                "palette": ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'orange', 'red']
            }
        elif variable == "vp":
            return {
                "min": 0.0,
                "max": 3000.0,
                "palette": ['white', 'blue', 'cyan', 'green', 'yellow', 'orange', 'red']
            }
        elif variable == "swe":
            return {
                "min": 0.0,
                "max": 1000.0,
                "palette": ['white', 'lightblue', 'blue', 'purple']
            }
        elif variable == "dayl":
            return {
                "min": 0.0,
                "max": 86400.0,
                "palette": ['black', 'blue', 'cyan', 'yellow', 'orange', 'red']
            }
    
    # NOAA GFS
    elif dataset_id == "NOAA/GFS0P25":
        if variable == "temperature_2m_above_ground":
            return {
                "min": -40.0,
                "max": 35.0,
                "palette": ['blue', 'purple', 'cyan', 'green', 'yellow', 'red']
            }
        elif "wind" in variable:
            return {
                "min": -30.0,
                "max": 30.0,
                "palette": ['blue', 'cyan', 'green', 'yellow', 'orange', 'red']
            }
        elif variable == "relative_humidity_2m_above_ground":
            return {
                "min": 0.0,
                "max": 100.0,
                "palette": ['red', 'orange', 'yellow', 'green', 'cyan', 'blue']
            }
        elif variable == "total_precipitation_surface":
            return {
                "min": 0.0,
                "max": 50.0,
                "palette": ['white', 'blue', 'cyan', 'green', 'yellow', 'orange', 'red']
            }
    
    # CHIRPS
    elif dataset_id == "UCSB-CHG/CHIRPS/DAILY":
        if variable == "precipitation":
            return {
                "min": 1.0,
                "max": 17.0,
                "palette": ['001137', '0aab1e', 'e7eb05', 'ff4a2d', 'e90000']
            }
    
    # GOES-16
    elif dataset_id == "NOAA/GOES/16/MCMIPC":
        if variable in ["CMI_C01", "CMI_C02", "CMI_C03", "CMI_C13"]:
            return {
                "min": 0.0,
                "max": 0.7,
                "gamma": 1.3,
                "palette": ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'orange', 'red', 'white']
            }
    
    # SRTM
    elif dataset_id == "USGS/SRTMGL1_003":
        if variable == "elevation":
            return {
                "min": 0.0,
                "max": 5000.0,
                "palette": ['006600', '002200', 'fff700', 'ab7634', 'c4d0ff', 'ffffff']
            }
    
    # GTOPO30
    elif dataset_id == "USGS/GTOPO30":
        if variable == "elevation":
            return {
                "min": -10.0,
                "max": 8000.0,
                "gamma": 1.6,
                "palette": ['0000ff', '00ffff', '00ff00', 'ffff00', 'ff0000', 'ffffff']
            }
    
    # Valeurs par défaut
    return {
        "min": 0,
        "max": 100,
        "palette": ['blue', 'cyan', 'green', 'yellow', 'orange', 'red']
    }

@app.route('/')
def index():
    """Page d'accueil de l'application."""
    return render_template('home.html', datasets=DATASETS)

@app.route('/viewer')
def viewer():
    """Page de visualisation d'un dataset spécifique."""
    # Récupérer les paramètres de l'URL
    dataset_id = request.args.get('dataset', 'NASA/ORNL/DAYMET_V4')
    
    # Obtenir les informations sur le dataset
    dataset_info = get_dataset_info(dataset_id)
    if not dataset_info:
        return "Dataset non trouvé", 404
    
    # Passer les informations au template
    return render_template('viewer.html', dataset=dataset_info, datasets=DATASETS)

@app.route('/api/test_connection')
def test_connection():
    """Test simple de la connexion à Earth Engine."""
    try:
        # Vérifier si Earth Engine est initialisé
        if not ee.data._initialized:
            initialize_earth_engine()
            if not ee.data._initialized:
                return jsonify({"status": "error", "message": "Échec de l'initialisation de Earth Engine"})
        
        # Test simple d'accès à l'API
        info = ee.Image(1).getInfo()
        
        if info:
            return jsonify({
                "status": "success", 
                "message": "Connexion à Earth Engine réussie!"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Échec de la connexion à Earth Engine"
            })
            
    except Exception as e:
        logger.error(f"Exception lors du test de connexion: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/get_image')
def get_image():
    """Génère une image statique à partir du dataset sélectionné."""
    try:
        # Récupérer les paramètres
        dataset_id = request.args.get('dataset', 'NASA/ORNL/DAYMET_V4')
        variable = request.args.get('variable', 'tmax')
        date_str = request.args.get('date', None)
        
        # Obtenir les informations sur le dataset
        dataset_info = get_dataset_info(dataset_id)
        if not dataset_info:
            return jsonify({"error": "Dataset non trouvé"}), 404
        
        # Si la date n'est pas fournie, utiliser la date par défaut du dataset
        if not date_str and dataset_info["default_date"]:
            date_str = dataset_info["default_date"]
        
        # Journal pour le débogage
        logger.info(f"Requête d'image pour dataset: {dataset_id}, variable: {variable}, date: {date_str}")
        
        # Vérifier si Earth Engine est initialisé
        if not ee.data._initialized:
            initialize_earth_engine()
            if not ee.data._initialized:
                return jsonify({"error": "Échec de l'initialisation de Earth Engine"})
        
        # Processus spécifique pour chaque type de dataset
        if dataset_id == "NASA/ORNL/DAYMET_V4":
            return process_daymet(dataset_id, variable, date_str, dataset_info)
        elif dataset_id == "NOAA/GFS0P25":
            return process_gfs(dataset_id, variable, date_str, dataset_info)
        elif dataset_id == "UCSB-CHG/CHIRPS/DAILY":
            return process_chirps(dataset_id, variable, date_str, dataset_info)
        elif dataset_id == "NOAA/GOES/16/MCMIPC":
            return process_goes16(dataset_id, variable, date_str, dataset_info)
        elif dataset_id in ["USGS/SRTMGL1_003", "USGS/GTOPO30"]:
            return process_dem(dataset_id, variable, dataset_info)
        else:
            return jsonify({"error": f"Traitement non implémenté pour le dataset {dataset_id}"}), 501
        
    except Exception as e:
        logger.error(f"Exception lors de la génération de l'image: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

def process_daymet(dataset_id, variable, date_str, dataset_info):
    """Traite les données DAYMET."""
    try:
        # Convertir la date
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        # On filtre sur un jour pour DAYMET (données quotidiennes)
        start_date = date_str
        end_date = (date_obj + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Accéder au dataset
        dataset = ee.ImageCollection(dataset_id) \
                    .filterDate(start_date, end_date)
        
        # Vérifier si des images sont disponibles
        collection_size = dataset.size().getInfo()
        logger.info(f"Nombre d'images trouvées: {collection_size}")
        
        if collection_size == 0:
            return jsonify({"error": f"Aucune donnée disponible pour cette date: {date_str}."})
        
        # Sélectionner la bande (variable)
        variable_collection = dataset.select(variable)
        
        # Prendre la première image
        image = variable_collection.first()
        
        # Paramètres de visualisation
        vis_params = get_vis_params(dataset_id, variable)
        
        # Définir la région à visualiser
        region = ee.Geometry.Rectangle(dataset_info["default_region"])
        
        # Obtenir l'URL de l'image
        image_url = image.getThumbURL({
            'dimensions': '1200x800',
            'format': 'png',
            'min': vis_params['min'],
            'max': vis_params['max'],
            'palette': vis_params['palette'],
            'region': region.toGeoJSON()
        })
        
        # Renvoyer l'URL de l'image
        return jsonify({
            "image_url": image_url,
            "vis_params": vis_params,
            "variable_name": next((v["name"] for v in dataset_info["variables"] if v["id"] == variable), variable)
        })
    
    except Exception as e:
        logger.error(f"Erreur lors du traitement DAYMET: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Erreur lors du traitement DAYMET: {str(e)}"}), 500

def process_gfs(dataset_id, variable, date_str, dataset_info):
    """Traite les données GFS."""
    try:
        # Convertir la date
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        # GFS a des données toutes les 6 heures, on filtre sur une journée
        start_date = date_str
        end_date = (date_obj + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Accéder au dataset
        dataset = ee.ImageCollection(dataset_id) \
                    .filterDate(start_date, end_date) \
                    .select(variable)
        
        # Vérifier si des images sont disponibles
        collection_size = dataset.size().getInfo()
        logger.info(f"Nombre d'images GFS trouvées: {collection_size}")
        
        if collection_size == 0:
            return jsonify({"error": f"Aucune donnée GFS disponible pour cette date: {date_str}."})
        
        # Utiliser la première image
        image = dataset.first()
        
        # Paramètres de visualisation
        vis_params = get_vis_params(dataset_id, variable)
        
        # Définir la région à visualiser
        region = ee.Geometry.Rectangle(dataset_info["default_region"])
        
        # Obtenir l'URL de l'image
        image_url = image.getThumbURL({
            'dimensions': '1200x800',
            'format': 'png',
            'min': vis_params['min'],
            'max': vis_params['max'],
            'palette': vis_params['palette'],
            'region': region.toGeoJSON()
        })
        
        # Renvoyer l'URL de l'image
        return jsonify({
            "image_url": image_url,
            "vis_params": vis_params,
            "variable_name": next((v["name"] for v in dataset_info["variables"] if v["id"] == variable), variable)
        })
    
    except Exception as e:
        logger.error(f"Erreur lors du traitement GFS: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Erreur lors du traitement GFS: {str(e)}"}), 500

def process_chirps(dataset_id, variable, date_str, dataset_info):
    """Traite les données CHIRPS."""
    try:
        # Convertir la date
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        # CHIRPS a des données quotidiennes
        start_date = date_str
        end_date = (date_obj + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Accéder au dataset
        dataset = ee.ImageCollection(dataset_id) \
                    .filterDate(start_date, end_date) \
                    .select(variable)
        
        # Vérifier si des images sont disponibles
        collection_size = dataset.size().getInfo()
        logger.info(f"Nombre d'images CHIRPS trouvées: {collection_size}")
        
        if collection_size == 0:
            return jsonify({"error": f"Aucune donnée CHIRPS disponible pour cette date: {date_str}."})
        
        # Utiliser la première image
        image = dataset.first()
        
        # Paramètres de visualisation
        vis_params = get_vis_params(dataset_id, variable)
        
        # Définir la région à visualiser
        region = ee.Geometry.Rectangle(dataset_info["default_region"])
        
        # Obtenir l'URL de l'image
        image_url = image.getThumbURL({
            'dimensions': '1200x800',
            'format': 'png',
            'min': vis_params['min'],
            'max': vis_params['max'],
            'palette': vis_params['palette'],
            'region': region.toGeoJSON()
        })
        
        # Renvoyer l'URL de l'image
        return jsonify({
            "image_url": image_url,
            "vis_params": vis_params,
            "variable_name": next((v["name"] for v in dataset_info["variables"] if v["id"] == variable), variable)
        })
    
    except Exception as e:
        logger.error(f"Erreur lors du traitement CHIRPS: {str(e)}")
        return jsonify({"error": f"Erreur lors du traitement CHIRPS: {str(e)}"}), 500

def process_goes16(dataset_id, variable, date_str, dataset_info):
    """Traite les données GOES-16."""
    try:
        # Les données GOES-16 sont complexes et nécessitent un traitement spécial
        if date_str is None:
            # Utiliser une date récente par défaut
            date_str = "2022-01-01"  # Date arbitraire pour l'exemple
        
        # Formater la date pour GOES-16
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        start_date = date_str
        end_date = (date_obj + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Accéder au dataset
        dataset = ee.ImageCollection(dataset_id) \
                    .filterDate(start_date, end_date) \
                    .select(variable)
        
        # Vérifier si des images sont disponibles
        collection_size = dataset.size().getInfo()
        logger.info(f"Nombre d'images GOES-16 trouvées: {collection_size}")
        
        if collection_size == 0:
            return jsonify({"error": f"Aucune donnée GOES-16 disponible pour cette date: {date_str}."})
        
        # Utiliser la première image
        image = dataset.first()
        
        # Paramètres de visualisation
        vis_params = get_vis_params(dataset_id, variable)
        
        # Définir la région à visualiser
        region = ee.Geometry.Rectangle(dataset_info["default_region"])
        
        # Créer les paramètres pour getThumbURL sans le gamma
        thumb_params = {
            'dimensions': '1200x800',
            'format': 'png',
            'min': vis_params['min'],
            'max': vis_params['max'],
            'palette': vis_params['palette'],
            'region': region.toGeoJSON()
        }
        
        # Obtenir l'URL de l'image
        image_url = image.getThumbURL(thumb_params)
        
        # Renvoyer l'URL de l'image
        return jsonify({
            "image_url": image_url,
            "vis_params": vis_params,
            "variable_name": next((v["name"] for v in dataset_info["variables"] if v["id"] == variable), variable)
        })
    
    except Exception as e:
        logger.error(f"Erreur lors du traitement GOES-16: {str(e)}")
        return jsonify({"error": f"Erreur lors du traitement GOES-16: {str(e)}"}), 500

def process_dem(dataset_id, variable, dataset_info):
    """Traite les données d'élévation (MNT)."""
    try:
        # Les données d'élévation sont statiques, pas besoin de date
        
        # Accéder au dataset
        image = ee.Image(dataset_id).select(variable)
        
        # Paramètres de visualisation
        vis_params = get_vis_params(dataset_id, variable)
        
        # Définir la région à visualiser
        region = ee.Geometry.Rectangle(dataset_info["default_region"])
        
        # Créer les paramètres pour getThumbURL sans le gamma si une palette est présente
        thumb_params = {
            'dimensions': '1200x800',
            'format': 'png',
            'min': vis_params['min'],
            'max': vis_params['max'],
            'palette': vis_params['palette'],
            'region': region.toGeoJSON()
        }
        
        # Ajouter gamma seulement s'il est présent ET qu'il n'y a pas de palette
        # Mais comme vous avez toujours une palette, cette condition ne s'appliquera pas
        if 'gamma' in vis_params and 'palette' not in vis_params:
            thumb_params['gamma'] = vis_params['gamma']
        
        # Obtenir l'URL de l'image
        image_url = image.getThumbURL(thumb_params)
        
        # Renvoyer l'URL de l'image
        return jsonify({
            "image_url": image_url,
            "vis_params": vis_params,
            "variable_name": next((v["name"] for v in dataset_info["variables"] if v["id"] == variable), variable)
        })
    
    except Exception as e:
        logger.error(f"Erreur lors du traitement DEM: {str(e)}")
        return jsonify({"error": f"Erreur lors du traitement DEM: {str(e)}"}), 500

@app.route('/static_image')
def static_image():
    """Affiche une image statique en plein écran avec légende."""
    try:
        # Récupérer les paramètres
        dataset_id = request.args.get('dataset', 'NASA/ORNL/DAYMET_V4')
        variable = request.args.get('variable', 'tmax')
        date_str = request.args.get('date', None)
        
        # Obtenir les informations sur le dataset
        dataset_info = get_dataset_info(dataset_id)
        if not dataset_info:
            return "Dataset non trouvé", 404
        
        # Si la date n'est pas fournie, utiliser la date par défaut du dataset
        if not date_str and dataset_info["default_date"]:
            date_str = dataset_info["default_date"]
        
        # Vérifier si Earth Engine est initialisé
        if not ee.data._initialized:
            initialize_earth_engine()
            if not ee.data._initialized:
                return "Échec de l'initialisation de Earth Engine", 500
        
        # Générer une image selon le type de dataset
        image_data = None
        if dataset_id == "NASA/ORNL/DAYMET_V4":
            # Traiter les données DAYMET
            response = process_daymet(dataset_id, variable, date_str, dataset_info)
            if isinstance(response, tuple):
                return f"Erreur: {response[0].json['error']}", response[1]
            image_data = response.json
        elif dataset_id == "NOAA/GFS0P25":
            # Traiter les données GFS
            response = process_gfs(dataset_id, variable, date_str, dataset_info)
            if isinstance(response, tuple):
                return f"Erreur: {response[0].json['error']}", response[1]
            image_data = response.json
        elif dataset_id == "UCSB-CHG/CHIRPS/DAILY":
            # Traiter les données CHIRPS
            response = process_chirps(dataset_id, variable, date_str, dataset_info)
            if isinstance(response, tuple):
                return f"Erreur: {response[0].json['error']}", response[1]
            image_data = response.json
        elif dataset_id == "NOAA/GOES/16/MCMIPC":
            # Traiter les données GOES-16
            response = process_goes16(dataset_id, variable, date_str, dataset_info)
            if isinstance(response, tuple):
                return f"Erreur: {response[0].json['error']}", response[1]
            image_data = response.json
        elif dataset_id in ["USGS/SRTMGL1_003", "USGS/GTOPO30"]:
            # Traiter les données d'élévation
            response = process_dem(dataset_id, variable, dataset_info)
            if isinstance(response, tuple):
                return f"Erreur: {response[0].json['error']}", response[1]
            image_data = response.json
        else:
            return f"Traitement non implémenté pour le dataset {dataset_id}", 501
        
        if not image_data:
            return "Erreur lors de la génération de l'image", 500
        
        # Extraire les paramètres nécessaires
        image_url = image_data.get("image_url")
        vis_params = image_data.get("vis_params")
        variable_name = image_data.get("variable_name")
        
        # Générer la légende
        palette = vis_params.get('palette', [])
        min_val = vis_params.get('min', 0)
        max_val = vis_params.get('max', 100)
        steps = len(palette)
        range_val = max_val - min_val
        
        legend_html = ""
        for i, color in enumerate(palette):
            value = min_val + (i * (range_val / (steps - 1)))
            color_code = color if color.startswith('#') else f"#{color}"
            legend_html += f"""
            <div class="legend-item">
                <div class="color-box" style="background-color: {color_code};"></div>
                <span>{value:.1f}</span>
            </div>
            """
        
        # Construire la page HTML
        dataset_name = dataset_info["name"]
        date_text = f"Date: {date_str}" if date_str else "Données statiques"
        
        return f"""
        <html>
            <head>
                <title>TerraSight - {dataset_name}</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        padding: 0;
                        margin: 0;
                        background-color: #f0f5f0;
                        color: #333;
                    }}
                    .header {{
                        background-color: #1e8449;
                        color: white;
                        padding: 15px;
                        text-align: center;
                        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                    }}
                    .container {{
                        max-width: 1400px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .image-container {{
                        margin-top: 20px;
                        text-align: center;
                        background-color: white;
                        padding: 10px;
                        border-radius: 8px;
                        box-shadow: 0 2px 15px rgba(0, 0, 0, 0.1);
                    }}
                    .image-container img {{
                        max-width: 100%;
                        border-radius: 4px;
                    }}
                    .controls {{
                        margin-top: 20px;
                        display: flex;
                        justify-content: center;
                        gap: 10px;
                    }}
                    .btn {{
                        text-decoration: none;
                        color: white;
                        background-color: #27ae60;
                        padding: 10px 20px;
                        border-radius: 4px;
                        font-weight: 500;
                        transition: background-color 0.2s ease;
                        border: none;
                        cursor: pointer;
                    }}
                    .btn:hover {{
                        background-color: #219653;
                    }}
                    .legend-container {{
                        margin-top: 20px;
                        padding: 15px;
                        background-color: white;
                        border-radius: 8px;
                        box-shadow: 0 2px 15px rgba(0, 0, 0, 0.1);
                    }}
                    .legend-title {{
                        text-align: center;
                        margin-bottom: 15px;
                        font-weight: 600;
                    }}
                    .legend {{
                        display: flex;
                        flex-wrap: wrap;
                        justify-content: center;
                        gap: 10px;
                    }}
                    .legend-item {{
                        display: flex;
                        align-items: center;
                        margin: 0 5px;
                    }}
                    .color-box {{
                        width: 20px;
                        height: 20px;
                        margin-right: 5px;
                        border-radius: 2px;
                    }}
                    .info-bar {{
                        background-color: #f8f9fa;
                        padding: 10px;
                        border-radius: 4px;
                        margin-top: 20px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>TerraSight</h1>
                    <p>Visualisation de données géospatiales avec Google Earth Engine</p>
                </div>
                
                <div class="container">
                    <h2>{dataset_name} - {variable_name}</h2>
                    <div class="info-bar">
                        <div>{date_text}</div>
                        <div>Dataset: {dataset_id}</div>
                    </div>
                    
                    <div class="image-container">
                        <img src="{image_url}" alt="{variable_name}" />
                    </div>
                    
                    <div class="legend-container">
                        <div class="legend-title">Légende</div>
                        <div class="legend">
                            {legend_html}
                        </div>
                    </div>
                    
                    <div class="controls">
                        <a href="/viewer?dataset={dataset_id}" class="btn">Retour à la visionneuse</a>
                        <a href="/" class="btn">Accueil</a>
                    </div>
                </div>
            </body>
        </html>
        """
    except Exception as e:
        import traceback
        return f"""
        <html>
            <head>
                <title>Erreur</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        padding: 20px;
                        background-color: #f8f9fa;
                    }}
                    .error {{
                        color: #721c24;
                        background-color: #f8d7da;
                        padding: 20px;
                        border-radius: 5px;
                        border: 1px solid #f5c6cb;
                        margin-bottom: 20px;
                    }}
                    pre {{
                        white-space: pre-wrap;
                        background-color: #f1f1f1;
                        padding: 15px;
                        border-radius: 4px;
                        overflow-x: auto;
                    }}
                    a {{
                        display: inline-block;
                        margin-top: 20px;
                        text-decoration: none;
                        color: white;
                        background-color: #27ae60;
                        padding: 10px 20px;
                        border-radius: 4px;
                    }}
                </style>
            </head>
            <body>
                <div class="error">
                    <h1>Erreur lors de la génération de l'image</h1>
                    <p>{str(e)}</p>
                    <pre>{traceback.format_exc()}</pre>
                    <a href="/">Retour à l'accueil</a>
                </div>
            </body>
        </html>
        """

# Servir les fichiers statiques
@app.route('/static/<path:filename>')
def static_files(filename):
    """Sert les fichiers statiques depuis le dossier 'static'."""
    return send_file(os.path.join('static', filename))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)