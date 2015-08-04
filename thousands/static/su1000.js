var INITIAL_COORDINATES = [ 54.480, 59.041 ]
var MSG_SERVER_ERROR = "Невозможно выполнить операцию: ошибка сервера"

function apiCall(uri, callback) {
    xmlhttp = new XMLHttpRequest();
    xmlhttp.open('GET', uri, true);
    xmlhttp.onreadystatechange = function() {
        if ( xmlhttp.readyState == 4 ) {
            if ( xmlhttp.status == 200 ) {
                callback(JSON.parse(xmlhttp.responseText));
            }
        }
    }
    xmlhttp.send(null);

}

function createMap(container, center, zoom) {
    var topo = new L.TileLayer('http://maps.marshruty.ru/ml.ashx?al=1&i=1&x={x}&y={y}&z={z}', {
        maxZoom: 15,
        minZoom: 8,
        attribution: "Генштабовские топокарты используют сервис <a href=\"http://www.marshruty.ru/Maps/Maps.aspx\">карты Маршруты.Ру</a>"
    }); 
    var osm = new L.TileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 20,
        minZoom: 8,
        attribution: "&copy; Участники <a href=\"http://www.openstreetmap.org/copyright\">OpenStreetMaps</a>"
    });
    var gs = new L.Google('SATELLITE', {
        maxZoom: 20,
        minZoom: 8
    });

    var map = L.map(container, { center: center, zoom: zoom, layers: osm  });
    var baseMaps = {
        "OpenStreetMaps": osm,
        "Топокарты": topo,
        "Google Sattelite": gs
    };
    L.control.layers(baseMaps).addTo(map);

    return map;
}

function pointPopupCode(feature) {
    name_alt = feature.properties.name_alt == "" ? "" : "<br/>" + feature.properties.name_alt;
    name = "<a href=\"/summit/" + feature.id + "\">" + feature.properties.name + "</a>";
    return name + name_alt +
        "<br>Высота: " + feature.properties.height + 
        "<br>Хребет:" + feature.properties.ridge + 
        "<br><button type=\"button\" class=\"btn btn-default btn-sm btn-block\">Отметить восхождение</button>";
}

function placePoints(data) {
    L.geoJson(data, {
        pointToLayer: function (feature, latlng) {
            var icon = L.MakiMarkers.icon({icon: "marker", color: "#" + feature.properties.color, size: "s"});
            return L.marker(latlng, {icon: icon}).bindPopup(pointPopupCode(feature));
        }
    }).addTo(map);
}

function createMainMap() {
    map = createMap('map', INITIAL_COORDINATES, 8);
    var hash = new L.Hash(map);
    apiCall('/api/summits', placePoints);
}


function setupCoordinatesPickMap() {
    map = createMap('coordinates-pick-map', INITIAL_COORDINATES, 8);
    map.scrollWheelZoom.disable();
    document.getElementsByClassName('leaflet-container')[0].style.cursor = 'crosshair';

    coordinates_field = document.getElementById('summit_edit_form').coordinates.value;
    if ( coordinates_field ) {
        lat = parseFloat(coordinates_field.split(' ')[0]);
        lng = parseFloat(coordinates_field.split(' ')[1]);
        marker = L.marker(L.latLng(lat, lng));
        marker.addTo(map);
    }
    map.on('click', getPointCoordinates);
}

function getPointCoordinates(e) {
    document.getElementById('summit_edit_form').coordinates.value = e.latlng.lat + ' ' + e.latlng.lng;
    if (marker != null) {
        map.removeLayer(marker);
    }
    marker = L.marker(e.latlng);
    marker.addTo(map);
}
