// app.js
// Variables globales
let map;
let tileLayer;

// Fonction pour afficher un message de statut
function showStatus(message, type) {
  const statusElement = document.getElementById('status');
  statusElement.textContent = message;
  statusElement.className = '';
  statusElement.classList.add('status-' + type);
  statusElement.style.display = 'block';
}

// Fonction pour masquer le message de statut
function hideStatus() {
  document.getElementById('status').style.display = 'none';
}

// Fonction pour afficher l'indicateur de chargement
function showLoading() {
  document.getElementById('loading').style.display = 'block';
}

// Fonction pour masquer l'indicateur de chargement
function hideLoading() {
  document.getElementById('loading').style.display = 'none';
}

// Initialiser la carte
function initMap() {
  // Créer la carte Leaflet
  map = L.map('map').setView([0, 0], 2);
  
  // Ajouter une couche de fond
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);
  
  // Charger les données initiales
  loadEarthEngineData();
  
  // Ajouter l'événement pour le bouton de mise à jour
  document.getElementById('update-map').addEventListener('click', loadEarthEngineData);
}

// Charger les données Earth Engine
function loadEarthEngineData() {
  // Récupérer les valeurs des contrôles
  const variable = document.getElementById('variable').value;
  const date = document.getElementById('date').value;
  
  showLoading();
  showStatus('Chargement des données...', 'loading');
  
  // Appeler l'API pour obtenir l'URL de tuile
  fetch(`/api/get_tile_url?variable=${variable}&date=${date}`)
    .then(response => {
      if (!response.ok) {
        return response.json().then(err => {
          throw new Error(err.error || 'Erreur lors de la récupération des données');
        });
      }
      return response.json();
    })
    .then(data => {
      hideLoading();
      
      if (data.error) {
        showStatus('Erreur: ' + data.error, 'error');
        return;
      }
      
      console.log('Données de tuiles reçues:', data);
      
      // Supprimer la couche précédente si elle existe
      if (tileLayer && map.hasLayer(tileLayer)) {
        map.removeLayer(tileLayer);
      }
      
      try {
        // Vérifier que l'URL est complète
        if (!data.tile_url) {
          throw new Error('URL de tuile manquante');
        }
        
        console.log('URL de tuile à utiliser:', data.tile_url);
        
        // Créer une nouvelle couche TileLayer
        tileLayer = L.tileLayer(data.tile_url, {
          attribution: 'Google Earth Engine | NOAA CFSR',
          opacity: 1.0,
          zIndex: 100  // Valeur élevée pour s'assurer qu'elle est au-dessus
        });
        
        // Ajouter la couche à la carte
        tileLayer.addTo(map);
        
        // Log pour débogage
        tileLayer.on('loading', function() {
          console.log('Chargement des tuiles...');
        });
        
        tileLayer.on('load', function() {
          console.log('Tuiles chargées!');
        });
        
        tileLayer.on('error', function(e) {
          console.error('Erreur de chargement des tuiles:', e);
        });
        
        // Mettre à jour la légende
        updateLegend(data.variable_name, data.vis_params);
        
        hideStatus();
        showStatus('Données chargées avec succès!', 'success');
        
        // Cacher le message de succès après 3 secondes
        setTimeout(hideStatus, 3000);
      } catch (e) {
        console.error('Erreur lors du chargement de la couche:', e);
        showStatus('Erreur lors du chargement de la couche: ' + e.message, 'error');
      }
    })
    .catch(error => {
      hideLoading();
      showStatus('Erreur: ' + error.message, 'error');
      console.error('Erreur lors du chargement des données:', error);
    });
}

// Mettre à jour la légende
function updateLegend(variableName, visParams) {
  const legendElement = document.getElementById('legend');
  legendElement.innerHTML = '';
  
  // Titre de la légende
  const title = document.createElement('div');
  title.className = 'legend-title';
  title.textContent = variableName;
  legendElement.appendChild(title);
  
  // Créer la légende en fonction des paramètres de visualisation
  const palette = visParams.palette;
  const min = visParams.min;
  const max = visParams.max;
  const steps = palette.length;
  const range = max - min;
  
  for (let i = 0; i < palette.length; i++) {
    const legendItem = document.createElement('div');
    legendItem.className = 'legend-item';
    
    const colorBox = document.createElement('div');
    colorBox.className = 'color-box';
    colorBox.style.backgroundColor = palette[i];
    
    const label = document.createElement('span');
    const value = min + (i * (range / (steps - 1)));
    label.textContent = value.toFixed(1);
    
    legendItem.appendChild(colorBox);
    legendItem.appendChild(label);
    legendElement.appendChild(legendItem);
  }
}

// Tester la connexion à Earth Engine
function testEarthEngineConnection() {
  fetch('/api/test_connection')
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        console.log('Connexion à Earth Engine réussie!');
        initMap();
      } else {
        showStatus('Erreur de connexion à Earth Engine: ' + data.message, 'error');
        console.error('Erreur de connexion:', data);
      }
    })
    .catch(error => {
      showStatus('Erreur de connexion au serveur: ' + error.message, 'error');
      console.error('Erreur:', error);
    });
}

// Exécuter au chargement de la page
window.onload = function() {
  testEarthEngineConnection();
};